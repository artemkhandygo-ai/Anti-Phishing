def check_urgency(features: dict) -> list[dict]:
    reasons = []
    urgency_count = features.get("urgency_words_count", 0)
    if urgency_count >= 2:
        reasons.append({
            "reason_code": "URGENT_LANGUAGE",
            "reason_text": "Письмо содержит выраженную срочность или давление на пользователя.",
            "severity": "medium",
            "score": 0.15,
        })
    elif urgency_count >= 1:
        reasons.append({
            "reason_code": "MILD_URGENCY",
            "reason_text": "В письме присутствуют слова, указывающие на спешку или давление по времени.",
            "severity": "low",
            "score": 0.08,
        })
    return reasons
