def check_financial_request(features: dict) -> list[dict]:
    reasons = []
    if features.get("has_financial_request", 0):
        severity = "high" if features.get("urgency_words_count", 0) > 0 else "medium"
        score = 0.28 if severity == "high" else 0.18
        reasons.append({
            "reason_code": "FINANCIAL_REQUEST",
            "reason_text": "Письмо содержит просьбу перевести деньги, оплатить счёт или выполнить иной финансовый перевод. Это типичный признак мошеннического давления.",
            "severity": severity,
            "score": score,
        })
    return reasons
