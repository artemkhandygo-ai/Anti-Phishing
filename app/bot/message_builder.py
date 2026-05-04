from app.core.config import settings

RISK_META = {
    "safe": {
        "title": "✅ Проверено новое письмо",
        "risk": "БЕЗОПАСНО",
        "recommendation": "Явных признаков фишинга не обнаружено.",
    },
    "suspicious": {
        "title": "⚠️ Проверено новое письмо",
        "risk": "ПОДОЗРИТЕЛЬНО",
        "recommendation": "Проверьте отправителя, ссылки и вложения перед любыми действиями.",
    },
    "phishing": {
        "title": "🚨 Проверено новое письмо",
        "risk": "ОПАСНО",
        "recommendation": "Не переходите по ссылкам и не вводите коды/пароли.",
    },
}

PHONE_RELATED_REASON_CODES = {
    "PHONE_NUMBER_SCAM",
    "PHONE_URGENCY",
}

PAYMENT_RELATED_REASON_CODES = {
    "PAYMENT_COLLECTION_PAGE",
    "FINANCIAL_REQUEST",
}

CREDENTIAL_RELATED_REASON_CODES = {
    "CREDENTIAL_COLLECTION_PAGE",
    "PASSWORD_REQUEST",
    "LOGIN_PAGE_LINK",
}


def _recommendation_for_reason_codes(risk_level: str, reason_codes: set[str]) -> str:
    if reason_codes & PHONE_RELATED_REASON_CODES:
        return (
            "Не звоните по указанному номеру, не сообщайте коды, пароли, паспортные "
            "или платёжные данные. Проверьте информацию через официальный сайт или "
            "известный вам номер организации."
        )

    if reason_codes & PAYMENT_RELATED_REASON_CODES:
        return "Не вводите данные банковской карты и не переводите деньги без проверки отправителя и домена сайта."

    if reason_codes & CREDENTIAL_RELATED_REASON_CODES:
        return "Не вводите логин, пароль, одноразовые коды или данные аккаунта на странице из письма."

    return RISK_META.get(risk_level, RISK_META["suspicious"])["recommendation"]


def _truncate(text: str | None, limit: int) -> str:
    value = (text or "").strip()
    if len(value) <= limit:
        return value
    return value[: limit - 3].rstrip() + "..."


def build_alert_message(incident, email_obj) -> str:
    meta = RISK_META.get(incident.risk_level, RISK_META["suspicious"])
    reason_objects = list(getattr(incident, "reasons", []))
    reason_codes = {getattr(reason, "reason_code", "") for reason in reason_objects}
    recommendation = _recommendation_for_reason_codes(incident.risk_level, reason_codes)
    reasons_list = [reason.reason_text for reason in reason_objects[:6]]
    if not reasons_list:
        if incident.risk_level == "safe":
            reasons_list = ["явных признаков фишинга не обнаружено"]
        else:
            reasons_list = ["обнаружены рискованные признаки"]

    reasons = "\n".join(f"- {item}" for item in reasons_list)
    body_block = ""
    if settings.TELEGRAM_INCLUDE_FULL_TEXT:
        body_text = _truncate(email_obj.text_body or email_obj.html_body or "", settings.TELEGRAM_FULL_TEXT_LIMIT)
        if body_text:
            body_block = f"\n\nТекст письма:\n{body_text}"

    feedback_hint = "\n\nНиже можно отметить результат анализа: безопасно, фишинг или ложное срабатывание."

    return (
        f"{meta['title']}\n\n"
        f"Тема: {email_obj.subject or '(без темы)'}\n"
        f"Отправитель: {email_obj.from_email or '(неизвестно)'}\n"
        f"Риск: {meta['risk']}\n"
        f"Итоговый балл: {incident.risk_score:.2f}\n"
        f"Баллы: ML={incident.ml_score:.2f}, rules={incident.rule_score:.2f}\n\n"
        f"Причины:\n{reasons}\n\n"
        f"Рекомендация:\n{recommendation}"
        f"{body_block}"
        f"{feedback_hint}"
    )
