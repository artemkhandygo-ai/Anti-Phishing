def check_promo_scam(features: dict) -> list[dict]:
    reasons = []

    if features.get("has_promo_scam", 0):
        reasons.append({
            "reason_code": "PROMO_SCAM",
            "reason_text": "Письмо похоже на сообщение о призе, бонусе, выигрыше или рекламно-мошенническую приманку.",
            "severity": "high",
            "score": 0.24,
        })

    if features.get("has_phone_number", 0) and features.get("has_promo_scam", 0):
        reasons.append({
            "reason_code": "PHONE_NUMBER_SCAM",
            "reason_text": "В письме есть телефонный номер вместе с призывом срочно позвонить или получить приз.",
            "severity": "high",
            "score": 0.18,
        })
    elif features.get("has_phone_number", 0) and features.get("urgency_words_count", 0) > 0:
        reasons.append({
            "reason_code": "PHONE_URGENCY",
            "reason_text": "В письме есть телефонный номер и элементы срочного давления.",
            "severity": "medium",
            "score": 0.08,
        })

    return reasons
