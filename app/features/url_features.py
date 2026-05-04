from __future__ import annotations

from app.core.config import settings
from app.network_checks.domain_security import inspect_url


SUSPICIOUS_HINTS = ("login", "verify", "auth", "secure", "account", "password", "bank")


def _needs_deep_inspection(link: str, index: int, links_count: int) -> bool:
    blob = (link or "").lower()
    suspicion_score = 0
    if any(item in blob for item in SUSPICIOUS_HINTS):
        suspicion_score += 1
    if blob.startswith("http://"):
        suspicion_score += 1
    if any(shortener in blob for shortener in ("bit.ly", "tinyurl", "t.co", "goo.gl", "cutt.ly")):
        suspicion_score += 1
    if index == 0 and links_count == 1:
        return True
    return suspicion_score >= 1


def extract_url_features(links: list[str]) -> dict:
    limited_links = links[: settings.URL_MAX_INSPECTED_LINKS_PER_EMAIL]
    inspections = []
    deep_budget = max(settings.URL_MAX_DEEP_FETCH_LINKS_PER_EMAIL, 0)
    for index, link in enumerate(limited_links):
        do_deep = deep_budget > 0 and _needs_deep_inspection(link, index, len(limited_links))
        inspections.append(
            inspect_url(
                link,
                perform_content_fetch=do_deep,
            )
        )
        if do_deep:
            deep_budget -= 1

    short_count = sum(item.get("is_shortened", 0) for item in inspections)
    domains = [item.get("registered_domain", "") for item in inspections if item.get("registered_domain")]
    suspicious_keywords = sum(item.get("contains_login_words", 0) for item in inspections)
    ip_hosts = sum(item.get("uses_ip_host", 0) for item in inspections)
    final_domain_changed = sum(item.get("resolved_domain_changed", 0) for item in inspections)
    no_https_count = sum(1 for item in inspections if item.get("domain") and not item.get("is_https", 0))
    login_page_hits = sum(item.get("looks_like_login_page", 0) for item in inspections)
    punycode_domains = sum(1 for item in inspections if item.get("domain", "").startswith("xn--") or ".xn--" in item.get("domain", ""))
    sensitive_forms = sum(item.get("page_has_sensitive_form", 0) for item in inspections)
    external_forms = sum(item.get("form_action_external", 0) for item in inspections)
    brand_mismatch_hits = sum(item.get("page_brand_mismatch", 0) for item in inspections)
    credential_collection_hits = sum(item.get("page_collects_credentials", 0) for item in inspections)
    payment_collection_hits = sum(item.get("page_collects_payment_data", 0) for item in inspections)
    high_conf_brand_hits = sum(1 for item in inspections if item.get("page_brand_confidence", 0) >= 4)
    return {
        "links_count": len(links),
        "inspected_links_count": len(limited_links),
        "shortened_links_count": int(short_count),
        "unique_link_domains": len(set(domains)),
        "suspicious_url_keywords_count": int(suspicious_keywords),
        "ip_url_count": int(ip_hosts),
        "resolved_domain_changed_count": int(final_domain_changed),
        "non_https_links_count": int(no_https_count),
        "login_page_hits": int(login_page_hits),
        "punycode_link_domains_count": int(punycode_domains),
        "sensitive_form_hits": int(sensitive_forms),
        "external_form_action_hits": int(external_forms),
        "brand_mismatch_hits": int(brand_mismatch_hits),
        "credential_collection_hits": int(credential_collection_hits),
        "payment_collection_hits": int(payment_collection_hits),
        "high_conf_brand_hits": int(high_conf_brand_hits),
        "link_inspections": inspections,
    }
