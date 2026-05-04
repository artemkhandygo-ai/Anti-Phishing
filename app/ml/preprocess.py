import re
from typing import Iterable
import pandas as pd

from app.utils.text_utils import (
    count_emails,
    count_financial_request_hits,
    count_phone_numbers,
    count_promo_scam_hits,
    count_urgency_words,
    count_urls,
    exclamation_count,
    has_financial_request,
    has_password_or_code_request,
    has_phone_number,
    has_promo_scam,
    uppercase_word_count,
)


def clean_text(text: str) -> str:
    text = str(text or "")
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_label(label) -> str:
    if isinstance(label, str):
        value = label.strip().lower()
        if value in {"ham", "legit", "safe", "0"}:
            return "safe"
        if value in {"spam", "phishing", "fraud", "1"}:
            return "phishing"
    try:
        return "phishing" if int(label) == 1 else "safe"
    except Exception:
        return "safe"


def unify_dataset(df: pd.DataFrame) -> pd.DataFrame:
    cols = set(df.columns)
    if {"text_combined", "label"} <= cols:
        out = pd.DataFrame({
            "text": df["text_combined"].astype(str),
            "label": df["label"].apply(normalize_label),
        })
        return out

    if {"text", "label"} <= cols:
        out = pd.DataFrame({
            "text": df["text"].astype(str),
            "label": df["label"].apply(normalize_label),
        })
        return out

    if {"subject", "body", "label"} <= cols:
        out = pd.DataFrame({
            "text": (df["subject"].fillna("").astype(str) + " " + df["body"].fillna("").astype(str)).astype(str),
            "label": df["label"].apply(normalize_label),
        })
        return out

    if {"v1", "v2"} <= cols:
        out = pd.DataFrame({
            "text": df["v2"].astype(str),
            "label": df["v1"].apply(normalize_label),
        })
        return out

    raise ValueError("Unknown dataset format")


def build_tabular_features(texts: Iterable[str]) -> pd.DataFrame:
    rows = []
    for text in texts:
        text = str(text or "")
        rows.append({
            "text_length": len(text),
            "urgency_words_count": count_urgency_words(text),
            "financial_request_hits": count_financial_request_hits(text),
            "has_financial_request": int(has_financial_request(text)),
            "has_password_request": int(has_password_or_code_request(text)),
            "promo_scam_hits": count_promo_scam_hits(text),
            "has_promo_scam": int(has_promo_scam(text)),
            "phone_numbers_count": count_phone_numbers(text),
            "has_phone_number": int(has_phone_number(text)),
            "inline_urls_count": count_urls(text),
            "inline_emails_count": count_emails(text),
            "exclamation_count": exclamation_count(text),
            "uppercase_words_count": uppercase_word_count(text),
            "links_count": count_urls(text),
            "shortened_links_count": 0,
            "unique_link_domains": 0,
            "suspicious_url_keywords_count": 0,
            "ip_url_count": 0,
            "resolved_domain_changed_count": 0,
            "non_https_links_count": 0,
            "login_page_hits": 0,
            "punycode_link_domains_count": 0,
            "from_reply_to_mismatch": 0,
            "sender_domain_has_mx": 0,
            "sender_domain_has_spf_dns": 0,
            "sender_domain_has_dmarc_dns": 0,
            "sender_domain_has_a_record": 0,
            "sender_domain_punycode": 0,
            "reply_domain_punycode": 0,
            "sender_ip_matches_domain": 0,
            "lookalike_reply_domain": 0,
            "received_ip_count": 0,
        })
    return pd.DataFrame(rows)
