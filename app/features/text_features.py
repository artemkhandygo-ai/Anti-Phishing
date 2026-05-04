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
    normalize_text,
    uppercase_word_count,
)


def extract_text_features(subject: str | None, body_text: str | None) -> dict:
    text = normalize_text(f"{subject or ''} {body_text or ''}")
    return {
        "combined_text": text,
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
    }
