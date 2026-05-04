from __future__ import annotations

import ipaddress
import json
import logging
import re
import socket
import time
from functools import lru_cache
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

import dns.resolver
import requests
from bs4 import BeautifulSoup

from app.core.config import settings
from app.utils.domain_tools import (
    domain_has_suspicious_words,
    domain_similarity,
    get_domain_from_url,
    get_registered_domain,
    is_punycode_domain,
    looks_like_typosquat,
    normalize_domain,
    url_uses_ip,
)
from app.utils.validators import SHORTENER_DOMAINS

LOGIN_HINTS = ["login", "signin", "verify", "account", "bank", "secure", "password", "auth", "sign in"]
CREDENTIAL_HINTS = ["password", "username", "email", "login", "otp", "one-time", "verification code", "2fa", "sms code"]
PAYMENT_HINTS = ["card", "cvv", "iban", "account number", "expiry", "payment", "billing"]
SENSITIVE_HINTS = CREDENTIAL_HINTS + PAYMENT_HINTS
HEADERS_UA = {"User-Agent": "Anti-Phishing/1.1 (+security mail analysis)"}
RECEIVED_IP_RE = re.compile(r"\[?(\d{1,3}(?:\.\d{1,3}){3})\]?")
FORM_ACTION_RE = re.compile(r"^(?:https?:)?//", re.I)
BRAND_PROFILES_PATH = Path(__file__).resolve().parents[1] / "data" / "config" / "brand_profiles.json"

logger = logging.getLogger(__name__)


def _http_get_with_retry(
    url: str,
    *,
    headers: dict | None = None,
    timeout: int | float = 12,
    allow_redirects: bool = True,
    retries: int = 1,
    retry_sleep_seconds: float = 1.0,
):
    last_exc = None
    request_timeout = (min(float(timeout), 5.0), float(timeout))
    for attempt in range(retries + 1):
        try:
            return requests.get(
                url,
                headers=headers or None,
                timeout=request_timeout,
                allow_redirects=allow_redirects,
            )
        except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectTimeout, requests.exceptions.SSLError) as exc:
            last_exc = exc
            if attempt < retries:
                time.sleep(retry_sleep_seconds)
                continue
            raise
        except requests.exceptions.RequestException as exc:
            last_exc = exc
            raise
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("HTTP request failed without exception")


@lru_cache(maxsize=1)
def _brand_profiles() -> dict[str, dict]:
    try:
        data = json.loads(BRAND_PROFILES_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}

    profiles: dict[str, dict] = {}
    for key, raw in data.items():
        aliases = sorted({str(item).strip().lower() for item in raw.get("aliases", []) if str(item).strip()})
        allowed_domains = sorted({normalize_domain(item) for item in raw.get("allowed_domains", []) if normalize_domain(item)})
        login_domains = sorted({normalize_domain(item) for item in raw.get("login_domains", []) if normalize_domain(item)})
        profiles[key] = {
            "display_name": raw.get("display_name", key),
            "aliases": aliases,
            "allowed_domains": allowed_domains,
            "login_domains": login_domains or allowed_domains,
        }
    return profiles


def _fallback_nameservers() -> list[str]:
    raw = settings.DOMAIN_SECURITY_RESOLVERS or ""
    return [item.strip() for item in raw.split(",") if item.strip()]


def _resolvers() -> list[dns.resolver.Resolver]:
    resolvers = [dns.resolver.get_default_resolver()]
    fallback = _fallback_nameservers()
    if fallback:
        custom = dns.resolver.Resolver(configure=False)
        custom.nameservers = fallback
        resolvers.append(custom)
    return resolvers


def _resolve_dns(name: str, rdtype: str, *, lifetime: float = 2.5):
    errors = []
    for resolver in _resolvers():
        try:
            return resolver.resolve(name, rdtype, lifetime=lifetime)
        except Exception as exc:  # pragma: no cover
            errors.append(exc)
            continue
    if errors:
        raise errors[-1]
    raise dns.resolver.NoAnswer


def _dns_txt_records(name: str) -> tuple[str, ...]:
    try:
        answers = _resolve_dns(name, "TXT")
        out: list[str] = []
        for rdata in answers:
            chunks = getattr(rdata, "strings", None)
            if chunks:
                out.append("".join(chunk.decode("utf-8", errors="ignore") for chunk in chunks))
            else:
                out.append(str(rdata).strip('"'))
        return tuple(out)
    except Exception:
        return tuple()


def _mx_hosts(domain: str) -> tuple[str, ...]:
    try:
        answers = _resolve_dns(domain, "MX")
        hosts = sorted({str(r.exchange).rstrip(".").lower() for r in answers})
        return tuple(hosts)
    except Exception:
        return tuple()


def _resolve_ipv4(host: str) -> tuple[str, ...]:
    host = normalize_domain(host)
    if not host:
        return tuple()
    try:
        answers = _resolve_dns(host, "A")
        ips = sorted({r.address for r in answers if getattr(r, "address", None)})
        if ips:
            return tuple(ips)
    except Exception:
        pass
    try:
        _, _, ips = socket.gethostbyname_ex(host)
        return tuple(sorted(set(ips)))
    except Exception:
        return tuple()


def _extract_received_ips(raw_headers: str | None) -> list[str]:
    if not raw_headers:
        return []
    ips = RECEIVED_IP_RE.findall(raw_headers)
    filtered = []
    for ip in ips:
        try:
            parsed = ipaddress.ip_address(ip)
            if parsed.version == 4:
                filtered.append(ip)
        except ValueError:
            continue
    return filtered


def _header_value(raw_headers: str | None, name: str) -> str:
    if not raw_headers:
        return ""
    pattern = re.compile(rf"^{re.escape(name)}:\s*(.+)$", re.I | re.M)
    match = pattern.search(raw_headers)
    return match.group(1).strip() if match else ""


def _spf_networks(domain: str, depth: int = 0, seen: tuple[str, ...] = ()) -> tuple[str, ...]:
    domain = normalize_domain(domain)
    if not domain or depth > 4 or domain in seen:
        return tuple()
    networks: set[str] = set()
    records = [r for r in _dns_txt_records(domain) if r.lower().startswith("v=spf1")]
    if not records:
        return tuple()
    tokens = records[0].split()
    for token in tokens[1:]:
        token = token.strip()
        if not token:
            continue
        mechanism = token.lstrip("+-~?")
        if mechanism.startswith("ip4:"):
            value = mechanism.split(":", 1)[1]
            try:
                networks.add(str(ipaddress.ip_network(value, strict=False)))
            except ValueError:
                continue
        elif mechanism == "a" or mechanism.startswith("a:"):
            target = domain if mechanism == "a" else normalize_domain(mechanism.split(":", 1)[1])
            for ip in _resolve_ipv4(target):
                networks.add(f"{ip}/32")
        elif mechanism == "mx" or mechanism.startswith("mx:"):
            target = domain if mechanism == "mx" else normalize_domain(mechanism.split(":", 1)[1])
            for host in _mx_hosts(target):
                for ip in _resolve_ipv4(host):
                    networks.add(f"{ip}/32")
        elif mechanism.startswith("include:"):
            include_domain = normalize_domain(mechanism.split(":", 1)[1])
            networks.update(_spf_networks(include_domain, depth + 1, seen + (domain,)))
        elif mechanism.startswith("redirect="):
            redirect_domain = normalize_domain(mechanism.split("=", 1)[1])
            networks.update(_spf_networks(redirect_domain, depth + 1, seen + (domain,)))
    return tuple(sorted(networks))


def _ip_matches_networks(ip: str, networks: tuple[str, ...]) -> bool:
    try:
        ip_obj = ipaddress.ip_address(ip)
    except ValueError:
        return False
    for net in networks:
        try:
            if ip_obj in ipaddress.ip_network(net, strict=False):
                return True
        except ValueError:
            continue
    return False


def inspect_domain(domain: str) -> dict:
    domain = normalize_domain(domain)
    base_info = {
        "registered_domain": get_registered_domain(domain),
        "domain_has_mx": 0,
        "domain_has_spf_dns": 0,
        "domain_has_dmarc_dns": 0,
        "domain_has_a_record": 0,
        "domain_is_punycode": int(is_punycode_domain(domain)) if domain else 0,
        "domain_suspicious_words": int(domain_has_suspicious_words(domain)) if domain else 0,
        "domain_mx_hosts": [],
        "domain_ips": [],
        "domain_spf_networks": [],
    }
    if not domain or not settings.DNS_CHECKS_ENABLED:
        return base_info

    txt_records = _dns_txt_records(domain)
    mx_hosts = list(_mx_hosts(domain))
    ips = list(_resolve_ipv4(domain))
    spf_networks = list(_spf_networks(domain))
    return {
        **base_info,
        "registered_domain": get_registered_domain(domain),
        "domain_has_mx": int(bool(mx_hosts)),
        "domain_has_spf_dns": int(any("v=spf1" in item.lower() for item in txt_records)),
        "domain_has_dmarc_dns": int(bool(_dns_txt_records(f"_dmarc.{domain}"))),
        "domain_has_a_record": int(bool(ips)),
        "domain_is_punycode": int(is_punycode_domain(domain)),
        "domain_suspicious_words": int(domain_has_suspicious_words(domain)),
        "domain_mx_hosts": mx_hosts,
        "domain_ips": ips,
        "domain_spf_networks": spf_networks,
    }


def _candidate_redirect_urls(url: str) -> list[str]:
    try:
        parsed = urlparse(url)
    except Exception:
        return []
    query = parse_qs(parsed.query, keep_blank_values=False)
    candidates: list[str] = []
    for key in ("url", "target", "redirect", "redirect_uri", "redirect_url", "redir", "dest", "destination", "next", "to"):
        for value in query.get(key, []):
            candidate = unquote((value or "").strip())
            if candidate.startswith(("http://", "https://")):
                candidates.append(candidate)
    return candidates


def _update_redirect_fields(info: dict, registered: str, final_url: str) -> None:
    final_domain = get_domain_from_url(final_url)
    info["final_url"] = final_url
    info["final_domain"] = final_domain
    info["resolved_domain_changed"] = int(bool(final_domain and get_registered_domain(final_domain) != registered))
    final_parsed = urlparse(final_url)
    final_blob = f"{final_domain}{final_parsed.path} {final_parsed.query}".lower()
    info["contains_login_words"] = int(info["contains_login_words"] or any(word in final_blob for word in LOGIN_HINTS))


def _absolute_form_action(base_url: str, action: str) -> str:
    if not action:
        return ""
    action = action.strip()
    if FORM_ACTION_RE.match(action):
        if action.startswith("//"):
            return f"https:{action}"
        return action
    parsed = urlparse(base_url)
    if action.startswith("/"):
        return f"{parsed.scheme}://{parsed.netloc}{action}"
    return f"{parsed.scheme}://{parsed.netloc}/{action}"


def _extract_page_signals(soup: BeautifulSoup) -> dict[str, str]:
    title = (soup.title.text.strip() if soup.title and soup.title.text else "")
    meta_parts = []
    for tag in soup.find_all("meta"):
        name = (tag.get("name") or tag.get("property") or "").lower()
        if name in {"description", "og:title", "og:description", "twitter:title", "twitter:description", "application-name"}:
            meta_parts.append((tag.get("content") or "").strip())
    alt_parts = [img.get("alt", "").strip() for img in soup.find_all("img") if img.get("alt")]
    button_parts = [btn.get_text(" ", strip=True) for btn in soup.find_all(["button", "a", "span", "div"])[:40] if hasattr(btn, "get_text")]
    label_parts = [lab.get_text(" ", strip=True) for lab in soup.find_all("label")[:20]]
    text = " ".join(soup.stripped_strings)
    return {
        "title": title,
        "meta": " ".join(meta_parts),
        "alts": " ".join(alt_parts),
        "buttons": " ".join(button_parts),
        "labels": " ".join(label_parts),
        "text": text,
    }


def _detect_brand(page_signals: dict[str, str], final_domain: str) -> dict:
    domain = normalize_domain(final_domain)
    registered = get_registered_domain(domain)
    scored: list[tuple[int, str, dict]] = []
    fields = {
        "title": page_signals.get("title", "").lower(),
        "meta": page_signals.get("meta", "").lower(),
        "alts": page_signals.get("alts", "").lower(),
        "buttons": page_signals.get("buttons", "").lower(),
        "labels": page_signals.get("labels", "").lower(),
        "text": page_signals.get("text", "").lower()[:7000],
    }
    for brand_key, profile in _brand_profiles().items():
        score = 0
        for alias in profile["aliases"]:
            alias_re = re.compile(rf"(?<![\w@.-]){re.escape(alias)}(?![\w@.-])", re.I)
            if alias_re.search(fields["title"]):
                score += 4
            if alias_re.search(fields["meta"]):
                score += 3
            if alias_re.search(fields["labels"]):
                score += 2
            if alias_re.search(fields["buttons"]):
                score += 2
            if alias_re.search(fields["alts"]):
                score += 2
            if alias_re.search(fields["text"]):
                score += 1
        if score:
            scored.append((score, brand_key, profile))

    scored.sort(reverse=True)
    if not scored:
        return {"brand": "", "confidence": 0, "mismatch": 0, "allowed": True}

    score, brand_key, profile = scored[0]
    allowed_domains = {get_registered_domain(item) for item in (profile["allowed_domains"] + profile["login_domains"]) if item}
    exact_allowed = {normalize_domain(item) for item in (profile["allowed_domains"] + profile["login_domains"]) if item}
    matches_allowed = registered in allowed_domains or domain in exact_allowed or any(domain.endswith(f".{item}") for item in exact_allowed)
    # generic bank-like brand without explicit domain allowlist should never trigger mismatch on name alone
    if not allowed_domains and not exact_allowed:
        mismatch = 0
    else:
        mismatch = int(score >= 4 and not matches_allowed)
    return {
        "brand": brand_key,
        "confidence": score,
        "mismatch": mismatch,
        "allowed": matches_allowed,
        "display_name": profile["display_name"],
    }


def inspect_url(url: str, *, perform_content_fetch: bool | None = None) -> dict:
    url = (url or "").strip()
    empty = {
        "domain": "",
        "registered_domain": "",
        "is_shortened": 0,
        "uses_ip_host": 0,
        "contains_login_words": 0,
        "is_https": 0,
        "final_url": "",
        "final_domain": "",
        "resolved_domain_changed": 0,
        "looks_like_login_page": 0,
        "page_title": "",
        "page_has_sensitive_form": 0,
        "page_brand_keyword": "",
        "page_brand_confidence": 0,
        "page_brand_mismatch": 0,
        "form_action_external": 0,
        "page_collects_credentials": 0,
        "page_collects_payment_data": 0,
    }
    if not url:
        return empty

    domain = get_domain_from_url(url)
    registered = get_registered_domain(domain)
    parsed = urlparse(url)
    if perform_content_fetch is None:
        perform_content_fetch = settings.URL_CONTENT_FETCH_ENABLED
    path_blob = f"{parsed.netloc}{parsed.path} {parsed.query}".lower()
    info = {
        **empty,
        "domain": domain,
        "registered_domain": registered,
        "is_shortened": int(domain in SHORTENER_DOMAINS),
        "uses_ip_host": int(url_uses_ip(url)),
        "contains_login_words": int(any(word in path_blob for word in LOGIN_HINTS)),
        "is_https": int(parsed.scheme.lower() == "https"),
    }


    if settings.URL_EXPANSION_ENABLED:
        response = None
        try:
            response = _http_get_with_retry(
                url,
                headers=HEADERS_UA,
                timeout=settings.URL_REQUEST_TIMEOUT_SECONDS,
                allow_redirects=True,
                retries=settings.URL_REQUEST_RETRIES,
                retry_sleep_seconds=settings.URL_REQUEST_RETRY_SLEEP_SECONDS,
            )
        except Exception as exc:
            logger.warning("inspect_url request failed for %s: %s", url, exc)
        if response is not None:
            try:
                final_url = response.url or url
                _update_redirect_fields(info, registered, final_url)
            except Exception as exc:
                logger.warning("inspect_url redirect processing failed for %s: %s", url, exc)
                final_url = url

            content_type = (response.headers.get("content-type", "") or "").lower()
            if perform_content_fetch and ("text/html" in content_type or content_type == ""):
                try:
                    snippet = (response.text or "")[: settings.URL_MAX_CONTENT_CHARS]
                except Exception as exc:
                    logger.warning("inspect_url reading response text failed for %s: %s", url, exc)
                    snippet = ""

                if snippet:
                    soup = None
                    for parser in ("lxml", "html.parser"):
                        try:
                            soup = BeautifulSoup(snippet, parser)
                            break
                        except Exception as exc:
                            logger.warning("inspect_url parser %s failed for %s: %s", parser, url, exc)
                    if soup is not None:
                        try:
                            signals = _extract_page_signals(soup)
                            title_lower = signals["title"].lower()
                            combined_text = " ".join(str(value) for value in signals.values()).lower()
                            inputs = soup.find_all("input")
                            password_inputs = soup.find_all("input", attrs={"type": re.compile(r"password", re.I)})
                            email_inputs = soup.find_all("input", attrs={"type": re.compile(r"email", re.I)})
                            hidden_inputs = soup.find_all("input", attrs={"type": re.compile(r"hidden", re.I)})
                            sensitive_name_inputs = [
                                item for item in inputs
                                if any(word in ((item.get("name") or "") + " " + (item.get("id") or "") + " " + (item.get("placeholder") or "")).lower() for word in CREDENTIAL_HINTS)
                            ]
                            payment_inputs = [
                                item for item in inputs
                                if any(word in ((item.get("name") or "") + " " + (item.get("id") or "") + " " + (item.get("placeholder") or "")).lower() for word in PAYMENT_HINTS)
                            ]
                            forms = soup.find_all("form")
                            form_count = len(forms)
                            action_hosts: set[str] = set()
                            final_registered = get_registered_domain(info.get("final_domain") or domain)
                            for form in forms:
                                action_url = _absolute_form_action(final_url, form.get("action", ""))
                                action_domain = get_domain_from_url(action_url)
                                if action_domain:
                                    action_hosts.add(get_registered_domain(action_domain))
                            keyword_hits = sum(word in combined_text for word in ["login", "sign in", "signin", "verify", "account", "password", "username", "email"])
                            sensitive_hits = sum(word in combined_text for word in SENSITIVE_HINTS)
                            brand_match = _detect_brand(signals, info.get("final_domain") or domain)
                            info["page_title"] = signals["title"][:180]
                            info["page_collects_credentials"] = int(bool(password_inputs or email_inputs or sensitive_name_inputs))
                            info["page_collects_payment_data"] = int(bool(payment_inputs))
                            info["page_has_sensitive_form"] = int(bool(password_inputs) or bool(payment_inputs) or sensitive_hits >= 2 or (form_count > 0 and len(hidden_inputs) >= 2 and keyword_hits >= 1))
                            info["looks_like_login_page"] = int(
                                bool(password_inputs)
                                or (form_count > 0 and len(inputs) >= 2 and keyword_hits >= 1)
                                or (len(inputs) >= 2 and keyword_hits >= 2)
                                or any(word in title_lower for word in LOGIN_HINTS)
                            )
                            info["form_action_external"] = int(bool(action_hosts and any(host != final_registered for host in action_hosts if host)))
                            info["page_brand_keyword"] = brand_match["brand"]
                            info["page_brand_confidence"] = int(brand_match["confidence"])
                            info["page_brand_mismatch"] = int(brand_match["mismatch"])
                        except Exception as exc:
                            logger.warning("inspect_url content analysis failed for %s: %s", url, exc)

    if not info["resolved_domain_changed"]:
        for candidate in _candidate_redirect_urls(url):
            _update_redirect_fields(info, registered, candidate)
            if info["resolved_domain_changed"]:
                break

    return info


def evaluate_trust_chain(raw_headers: str | None, from_email: str | None, reply_to_email: str | None) -> dict:
    from_domain = normalize_domain((from_email or "").split("@")[-1] if "@" in (from_email or "") else from_email)
    reply_domain = normalize_domain((reply_to_email or "").split("@")[-1] if "@" in (reply_to_email or "") else reply_to_email)
    auth_results = _header_value(raw_headers, "Authentication-Results")
    return_path = _header_value(raw_headers, "Return-Path")
    reply_mismatch = int(bool(reply_domain and from_domain and get_registered_domain(reply_domain) != get_registered_domain(from_domain)))

    domain_info = inspect_domain(from_domain)
    reply_info = inspect_domain(reply_domain) if reply_domain else inspect_domain("")
    received_ips = _extract_received_ips(raw_headers)

    mx_ips: set[str] = set()
    for host in domain_info.get("domain_mx_hosts", []):
        mx_ips.update(_resolve_ipv4(host))

    sender_ip_mx_comparable = int(bool(received_ips and mx_ips))
    sender_ip_matches_domain = int(bool(sender_ip_mx_comparable and any(ip in mx_ips for ip in received_ips)))

    spf_networks = tuple(domain_info.get("domain_spf_networks", []))
    sender_ip_spf_comparable = int(bool(received_ips and spf_networks))
    sender_ip_matches_spf = int(bool(sender_ip_spf_comparable and any(_ip_matches_networks(ip, spf_networks) for ip in received_ips)))

    infrastructure_ips = set(mx_ips) | set(domain_info.get("domain_ips", []))
    sender_ip_infrastructure_comparable = int(bool(received_ips and (infrastructure_ips or spf_networks)))
    sender_ip_matches_infrastructure = int(bool(any(ip in infrastructure_ips for ip in received_ips) or any(_ip_matches_networks(ip, spf_networks) for ip in received_ips)))

    lookalike_reply = int(bool(reply_domain and from_domain and looks_like_typosquat(reply_domain, [from_domain])))
    return_path_domain = normalize_domain(return_path.strip("<>").split("@")[-1] if "@" in return_path else return_path)

    return {
        "from_domain": from_domain,
        "reply_to_domain": reply_domain,
        "return_path_domain": return_path_domain,
        "auth_results_header": auth_results,
        "from_reply_to_mismatch": reply_mismatch,
        "sender_domain_has_mx": domain_info["domain_has_mx"],
        "sender_domain_has_spf_dns": domain_info["domain_has_spf_dns"],
        "sender_domain_has_dmarc_dns": domain_info["domain_has_dmarc_dns"],
        "sender_domain_has_a_record": domain_info["domain_has_a_record"],
        "sender_domain_punycode": domain_info["domain_is_punycode"],
        "sender_domain_suspicious_words": domain_info["domain_suspicious_words"],
        "reply_domain_punycode": reply_info["domain_is_punycode"],
        "reply_domain_has_mx": reply_info["domain_has_mx"],
        "received_ip_count": len(received_ips),
        "received_ips": received_ips,
        "sender_ip_mx_comparable": sender_ip_mx_comparable,
        "sender_ip_matches_domain": sender_ip_matches_domain,
        "sender_ip_spf_comparable": sender_ip_spf_comparable,
        "sender_ip_matches_spf": sender_ip_matches_spf,
        "sender_ip_infrastructure_comparable": sender_ip_infrastructure_comparable,
        "sender_ip_matches_infrastructure": sender_ip_matches_infrastructure,
        "lookalike_reply_domain": lookalike_reply,
        "reply_domain_similarity": domain_similarity(from_domain, reply_domain) if reply_domain else 0.0,
    }
