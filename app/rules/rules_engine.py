from app.rules.attachment_rules import check_attachments
from app.rules.financial_rules import check_financial_request
from app.rules.link_rules import check_links
from app.rules.promo_rules import check_promo_scam
from app.rules.sender_rules import check_sender
from app.rules.urgency_rules import check_urgency


def run_rules(features: dict) -> dict:
    reasons = []
    for checker in (check_sender, check_links, check_urgency, check_financial_request, check_promo_scam, check_attachments):
        reasons.extend(checker(features))

    if features.get("has_password_request", 0):
        reasons.append({
            "reason_code": "PASSWORD_REQUEST",
            "reason_text": "Письмо запрашивает пароль, код подтверждения или аналогичные чувствительные данные.",
            "severity": "high",
            "score": 0.25,
        })

    rule_score = round(sum(item["score"] for item in reasons), 4)
    return {
        "rule_score": min(rule_score, 1.0),
        "reasons": reasons,
    }
