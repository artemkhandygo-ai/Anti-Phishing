def check_attachments(features: dict) -> list[dict]:
    reasons = []
    if features.get("dangerous_attachments_count", 0) > 0:
        reasons.append({
            "reason_code": "DANGEROUS_ATTACHMENT",
            "reason_text": "Обнаружено потенциально опасное вложение.",
            "severity": "high",
            "score": 0.25,
        })
    return reasons
