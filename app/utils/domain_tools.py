from __future__ import annotations

import re
from difflib import SequenceMatcher
from urllib.parse import urlparse

import tldextract

_TLD = tldextract.TLDExtract(suffix_list_urls=None)

PUNYCODE_PREFIX = "xn--"
SUSPICIOUS_DOMAIN_WORDS = {"verify", "security", "update", "billing", "support", "login", "auth"}


def normalize_domain(domain: str | None) -> str:
    domain = (domain or "").strip().lower()
    if not domain:
        return ""
    domain = domain.split(":")[0]
    if domain.startswith("www."):
        domain = domain[4:]
    return domain


def get_registered_domain(value: str | None) -> str:
    domain = normalize_domain(value)
    if not domain:
        return ""
    extracted = _TLD(domain)
    if extracted.domain and extracted.suffix:
        return f"{extracted.domain}.{extracted.suffix}"
    return domain


def is_punycode_domain(domain: str | None) -> bool:
    parts = normalize_domain(domain).split(".")
    return any(part.startswith(PUNYCODE_PREFIX) for part in parts if part)


def domain_similarity(a: str | None, b: str | None) -> float:
    da = get_registered_domain(a)
    db = get_registered_domain(b)
    if not da or not db:
        return 0.0
    return SequenceMatcher(None, da, db).ratio()




def _normalize_confusables(domain: str | None) -> str:
    normalized = get_registered_domain(domain)
    if not normalized:
        return ""
    replacements = (
        ("rn", "m"),
        ("vv", "w"),
        ("0", "o"),
        ("1", "l"),
        ("!", "i"),
        ("5", "s"),
    )
    for src, dst in replacements:
        normalized = normalized.replace(src, dst)
    return normalized

def looks_like_typosquat(domain: str | None, reference_domains: list[str] | tuple[str, ...]) -> bool:
    test_domain = get_registered_domain(domain)
    if not test_domain:
        return False
    for ref in reference_domains:
        ref_domain = get_registered_domain(ref)
        if not ref_domain or ref_domain == test_domain:
            continue
        if _normalize_confusables(test_domain) == _normalize_confusables(ref_domain):
            return True
        similarity = domain_similarity(test_domain, ref_domain)
        if similarity >= 0.82:
            return True
    return False


def domain_has_suspicious_words(domain: str | None) -> bool:
    registered = get_registered_domain(domain)
    if not registered:
        return False
    parts = re.split(r"[\.-]", registered)
    return any(part in SUSPICIOUS_DOMAIN_WORDS for part in parts)


def get_domain_from_url(url: str | None) -> str:
    try:
        return normalize_domain(urlparse(url or "").netloc)
    except Exception:
        return ""


def url_uses_ip(url: str | None) -> bool:
    host = get_domain_from_url(url)
    return bool(re.fullmatch(r"\d{1,3}(?:\.\d{1,3}){3}", host))
