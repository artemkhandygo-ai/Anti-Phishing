def explain_prediction(features: dict, rule_reasons: list[dict]) -> list[str]:
    reasons = [item["reason_text"] for item in rule_reasons]
    if not reasons and features.get("text_length", 0) < 30:
        reasons.append("Письмо слишком короткое и не содержит достаточного контекста.")
    return reasons[:5]
