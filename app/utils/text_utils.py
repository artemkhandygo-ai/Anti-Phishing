import re

URGENT_WORDS_RU = [
    "срочно", "немедленно", "подтвердите", "заблокирован", "безопасность",
    "подтверждение", "код", "пароль", "восстановить", "войти",
    "быстро", "нет времени", "сейчас", "прямо сейчас", "срочно нужно",
]
URGENT_WORDS_EN = [
    "urgent", "immediately", "verify", "blocked", "security",
    "password", "code", "confirm", "reset",
    "asap", "right now", "no time", "quickly", "immediate action", "call now",
]

PASSWORD_PATTERNS = [
    "пароль", "password", "код подтверждения", "verification code", "otp",
    "one-time code", "2fa code", "код из смс", "pin code",
]

FINANCIAL_REQUEST_PATTERNS_RU = [
    "отправь деньги", "переведи деньги", "скинь деньги", "скинь на карту",
    "переведи на счет", "переведи на счёт", "оплати", "срочно оплати",
    "займи денег", "нужны деньги", "на мой счет", "на мой счёт",
    "по реквизитам", "перевод на карту", "отправь на карту", "оплати счет",
    "оплати счёт", "нужен перевод", "перешли деньги", "сделай перевод",
]
FINANCIAL_REQUEST_PATTERNS_EN = [
    "send money", "transfer money", "wire money", "wire funds",
    "send funds", "make a payment", "pay this", "urgent payment",
    "need money", "transfer to my account", "to my account",
    "bank transfer", "make the transfer", "send it now", "pay urgently",
    "send to my card", "payment required",
]

PROMO_SCAM_PATTERNS_RU = [
    "поздравляем", "вы выиграли", "вы победитель", "получите приз", "ваш приз",
    "бесплатный билет", "бесплатный пропуск", "акция", "подарок", "бонус",
    "позвоните сейчас", "срочно позвоните", "специальное предложение", "заберите выигрыш",
]
PROMO_SCAM_PATTERNS_EN = [
    "congrats", "congratulations", "you won", "winner", "claim your prize",
    "free ticket", "free pass", "special pass", "reward", "gift card",
    "call now", "special offer", "claim now", "limited offer", "free entry",
]

MONEY_WORDS_RU = ["деньги", "счет", "счёт", "карта", "реквизит", "перевод", "оплата", "оплатить"]
MONEY_WORDS_EN = ["money", "account", "card", "bank", "payment", "pay", "wire", "transfer"]

URL_RE = re.compile(r"(https?://\S+|www\.\S+)", re.I)
EMAIL_RE = re.compile(r"\b[\w\.-]+@[\w\.-]+\.\w+\b", re.I)
PHONE_RE = re.compile(
    r"(?:(?:\+?\d{1,3}[\s\-]?)?(?:\(?\d{2,4}\)?[\s\-]?)?\d{3,4}[\s\-]?\d{3,4}(?:[\s\-]?\d{2,4})?)"
)


def normalize_text(text: str) -> str:
    text = text or ""
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def strip_urls_for_text_rules(text: str) -> str:
    """Remove URLs and emails before text-only rules count words inside them."""
    text = URL_RE.sub(" ", text or "")
    text = EMAIL_RE.sub(" ", text)
    return normalize_text(text)


def count_urgency_words(text: str) -> int:
    text_l = strip_urls_for_text_rules(text).lower()
    return sum(text_l.count(word) for word in URGENT_WORDS_RU + URGENT_WORDS_EN)


def has_password_or_code_request(text: str) -> bool:
    text_l = (text or "").lower()
    return any(pattern in text_l for pattern in PASSWORD_PATTERNS)


def count_financial_request_hits(text: str) -> int:
    text_l = (text or "").lower()
    phrase_hits = sum(1 for pattern in FINANCIAL_REQUEST_PATTERNS_RU + FINANCIAL_REQUEST_PATTERNS_EN if pattern in text_l)
    money_hits = sum(text_l.count(word) for word in MONEY_WORDS_RU + MONEY_WORDS_EN)
    return phrase_hits + money_hits


def has_financial_request(text: str) -> bool:
    text_l = (text or "").lower()
    if any(pattern in text_l for pattern in FINANCIAL_REQUEST_PATTERNS_RU + FINANCIAL_REQUEST_PATTERNS_EN):
        return True
    urgency_present = any(word in text_l for word in URGENT_WORDS_RU + URGENT_WORDS_EN)
    money_present = any(word in text_l for word in MONEY_WORDS_RU + MONEY_WORDS_EN)
    return urgency_present and money_present


def count_promo_scam_hits(text: str) -> int:
    text_l = (text or "").lower()
    return sum(1 for pattern in PROMO_SCAM_PATTERNS_RU + PROMO_SCAM_PATTERNS_EN if pattern in text_l)


def has_promo_scam(text: str) -> bool:
    text_l = (text or "").lower()
    return any(pattern in text_l for pattern in PROMO_SCAM_PATTERNS_RU + PROMO_SCAM_PATTERNS_EN)


def count_phone_numbers(text: str) -> int:
    text = text or ""
    # require at least 7 digits total to avoid false positives on small numbers
    matches = []
    for m in PHONE_RE.findall(text):
        digits = re.sub(r"\D", "", m)
        if len(digits) >= 7:
            matches.append(m)
    return len(matches)


def has_phone_number(text: str) -> bool:
    return count_phone_numbers(text) > 0


def count_urls(text: str) -> int:
    return len(URL_RE.findall(text or ""))


def count_emails(text: str) -> int:
    return len(EMAIL_RE.findall(text or ""))


def exclamation_count(text: str) -> int:
    return (text or "").count("!")


def uppercase_word_count(text: str) -> int:
    count = 0
    for token in re.findall(r"\b[A-ZА-Я]{3,}\b", text or ""):
        count += 1
    return count
