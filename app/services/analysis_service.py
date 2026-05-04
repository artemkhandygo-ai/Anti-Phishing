from __future__ import annotations

import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import EmailAttachment, EmailLink, IncidentReason
from app.db.repositories import EmailRepository, IncidentRepository
from app.features.feature_pipeline import build_features
from app.network_checks.domain_security import inspect_url
from app.ml.predict import predict_email_text
from app.parser.email_parser import parse_message
from app.rules.rules_engine import run_rules
from app.services.notification_service import queue_incident_notification
from app.utils.whitelist import is_whitelisted_email

logger = logging.getLogger(__name__)

HIGH_RISK_REASON_CODES = {
    "PASSWORD_REQUEST",
    "DANGEROUS_ATTACHMENT",
    "AUTH_FAIL",
    "FINANCIAL_REQUEST",
    "PROMO_SCAM",
    "PHONE_NUMBER_SCAM",
    "LOOKALIKE_REPLY_DOMAIN",
    "LOGIN_PAGE_LINK",
    "IP_URL",
    "EXTERNAL_FORM_ACTION",
    "BRAND_MISMATCH_PAGE",
}

CRITICAL_REASON_CODES = {
    "EXTERNAL_FORM_ACTION",
    "BRAND_MISMATCH_PAGE",
    "CREDENTIAL_COLLECTION_PAGE",
    "PAYMENT_COLLECTION_PAGE",
}


def _create_reason(reason_code: str, reason_text: str, severity: str = "low") -> dict:
    return {
        "reason_code": reason_code,
        "reason_text": reason_text,
        "severity": severity,
        "score": 0.0,
    }


def _is_structurally_benign(features: dict) -> bool:
    return all([
        features.get("links_count", 0) == 0,
        features.get("attachments_count", 0) == 0,
        features.get("dangerous_attachments_count", 0) == 0,
        features.get("has_password_request", 0) == 0,
        features.get("has_financial_request", 0) == 0,
        features.get("has_promo_scam", 0) == 0,
        features.get("has_phone_number", 0) == 0,
        features.get("urgency_words_count", 0) == 0,
        features.get("suspicious_sender", 0) == 0,
        features.get("from_reply_to_mismatch", 0) == 0,
    ])


def decide_risk(rule_score: float, ml_label: str, ml_score: float, features: dict, reasons: list[dict]) -> tuple[str, float, list[dict]]:
    combined = min(max((rule_score * 0.55) + (ml_score * 0.45), 0.0), 1.0)
    reason_codes = {item["reason_code"] for item in reasons}
    high_risk_reasons = {item["reason_code"] for item in reasons if item["reason_code"] in HIGH_RISK_REASON_CODES}
    critical_reasons = {item["reason_code"] for item in reasons if item["reason_code"] in CRITICAL_REASON_CODES}
    structurally_benign = _is_structurally_benign(features)

    if critical_reasons:
        return "phishing", max(combined, 0.85), reasons

    if features.get("has_financial_request", 0):
        if ml_label in {"phishing", "suspicious"} or rule_score >= 0.18 or features.get("urgency_words_count", 0) > 0:
            return "phishing", max(combined, 0.82), reasons
        return "suspicious", max(combined, 0.58), reasons + [_create_reason("FINANCIAL_REVIEW", "Финансовый запрос без ссылок и вложений всё равно требует ручной проверки.", "medium")]

    if features.get("has_promo_scam", 0):
        if features.get("has_phone_number", 0) or ml_score >= 0.72 or rule_score >= 0.25:
            return "phishing", max(combined, 0.80), reasons
        return "suspicious", max(combined, 0.62), reasons + [_create_reason("PROMO_REVIEW", "Сообщение похоже на призовую или рекламно-мошенническую приманку и требует проверки.", "medium")]

    if features.get("has_password_request", 0) and (features.get("links_count", 0) > 0 or features.get("from_reply_to_mismatch", 0)):
        return "phishing", max(combined, 0.84), reasons

    if structurally_benign:
        auth_fail_count = int(features.get("auth_fail_count", 0) or 0)
        if auth_fail_count >= 3:
            return "phishing", max(combined, 0.76), reasons + [_create_reason("BENIGN_CONTENT_BUT_AUTH_FAIL", "Текст письма выглядит нейтрально, но все базовые проверки аутентификации провалены. Это сильный сигнал подмены отправителя.", "high")]
        if auth_fail_count == 2:
            return "suspicious", max(combined, 0.60), reasons + [_create_reason("BENIGN_CONTENT_BUT_AUTH_FAIL", "Текст письма выглядит нейтрально, но две базовые почтовые проверки не пройдены, поэтому письмо требует ручной проверки.", "medium")]
        if auth_fail_count == 1:
            return "suspicious", max(combined, 0.46), reasons + [_create_reason("BENIGN_CONTENT_BUT_AUTH_FAIL", "Письмо выглядит нейтрально по содержанию, но одна из аутентификационных проверок не пройдена, поэтому риск повышен до подозрительного.", "low")]
        if ml_label == "phishing":
            if ml_score >= 0.86 and high_risk_reasons:
                return "suspicious", min(max(combined, 0.58), 0.74), reasons + [_create_reason("BENIGN_PATTERN_DOWNGRADE", "Письмо выглядит бытовым или нейтральным, поэтому риск снижен до подозрительного и требует ручной проверки.", "low")]
            if ml_score >= 0.68:
                return "suspicious", min(max(combined, 0.52), 0.68), reasons + [_create_reason("BENIGN_PATTERN_DOWNGRADE", "У письма нет типичных структурных признаков фишинга, поэтому высокий риск автоматически снижен.", "low")]
            return "safe", min(combined, 0.22), reasons + [_create_reason("BENIGN_PATTERN", "Письмо не содержит ссылок, вложений, срочных требований или запросов пароля/кода и выглядит безопасным.", "low")]
        return "safe", min(combined, 0.18), reasons + [_create_reason("BENIGN_PATTERN", "Письмо не содержит ссылок, вложений, срочных требований или запросов пароля/кода и выглядит безопасным.", "low")]

    if ml_label == "phishing" and (ml_score >= 0.80 or rule_score >= 0.45 or high_risk_reasons):
        return "phishing", max(combined, ml_score), reasons

    if combined >= 0.74 and (
        features.get("links_count", 0) > 0
        or features.get("dangerous_attachments_count", 0) > 0
        or features.get("has_password_request", 0) > 0
        or features.get("has_phone_number", 0) > 0
    ):
        return "phishing", combined, reasons

    if combined >= 0.34 or ml_score >= 0.56 or rule_score >= 0.18 or high_risk_reasons:
        return "suspicious", combined, reasons

    return "safe", combined, reasons


def analyze_parsed_email(db: Session, parsed_email: dict):
    email_repo = EmailRepository(db)
    incident_repo = IncidentRepository(db)

    existing = email_repo.get_by_imap_uid(parsed_email.get("imap_uid"))
    if existing is None:
        existing = email_repo.get_by_message_id(parsed_email.get("message_id"))
    if existing is not None:
        return None

    try:
        email_obj = email_repo.create(
            imap_uid=parsed_email.get("imap_uid"),
            message_id=parsed_email.get("message_id"),
            subject=parsed_email.get("subject"),
            from_email=parsed_email.get("from_email"),
            from_name=parsed_email.get("from_name"),
            received_at=parsed_email.get("received_at"),
            text_body=parsed_email.get("text_body"),
            html_body=parsed_email.get("html_body"),
            raw_headers=parsed_email.get("raw_headers"),
        )
    except IntegrityError:
        db.rollback()
        existing = email_repo.get_by_imap_uid(parsed_email.get("imap_uid")) or email_repo.get_by_message_id(parsed_email.get("message_id"))
        logger.info("Skipped duplicate email message_id=%s imap_uid=%s", parsed_email.get("message_id"), parsed_email.get("imap_uid"))
        return existing

    features = build_features(parsed_email)
    link_inspections = list(features.get("link_inspections", []))

    for idx, link in enumerate(parsed_email.get("links", [])):
        link_info = link_inspections[idx] if idx < len(link_inspections) else inspect_url(link)
        db.add(EmailLink(
            email_id=email_obj.id,
            url=link,
            domain=link_info.get("registered_domain") or link_info.get("domain"),
            is_shortened=bool(link_info.get("is_shortened", 0)),
            is_suspicious=bool(
                link_info.get("contains_login_words", 0)
                or link_info.get("uses_ip_host", 0)
                or link_info.get("resolved_domain_changed", 0)
                or link_info.get("looks_like_login_page", 0)
            ),
        ))

    for att in parsed_email.get("attachments", []):
        db.add(EmailAttachment(
            email_id=email_obj.id,
            filename=att.get("filename"),
            content_type=att.get("content_type"),
            size=att.get("size"),
            extension=att.get("extension"),
            is_suspicious=False,
        ))

    if is_whitelisted_email(parsed_email.get("from_email")):
        reasons = [_create_reason("WHITELISTED_SENDER", "Отправитель находится в белом списке и автоматически считается безопасным.", "low")]
        prediction = {"label": "safe", "score": 0.0, "probabilities": {"safe": 1.0, "phishing": 0.0}, "model_version": "whitelist_override"}
        risk_level, risk_score = "safe", 0.0
        rule_score = 0.0
    else:
        rules_result = run_rules(features)
        prediction = predict_email_text(features["combined_text"], features=features)
        risk_level, risk_score, reasons = decide_risk(
            rule_score=rules_result["rule_score"],
            ml_label=prediction["label"],
            ml_score=prediction["score"],
            features=features,
            reasons=rules_result["reasons"],
        )
        rule_score = rules_result["rule_score"]

    incident = incident_repo.create(
        email_id=email_obj.id,
        risk_level=risk_level,
        risk_score=risk_score,
        rule_score=rule_score,
        ml_score=prediction["score"],
        model_version=prediction["model_version"],
        status="new",
    )

    for reason in reasons:
        db.add(IncidentReason(
            incident_id=incident.id,
            reason_code=reason["reason_code"],
            reason_text=reason["reason_text"],
            severity=reason["severity"],
        ))

    db.commit()
    db.refresh(incident)
    db.refresh(email_obj)

    queue_incident_notification(incident.id)
    return incident


def analyze_message_object(db: Session, message_obj, imap_uid: str | None = None):
    parsed_email = parse_message(message_obj, imap_uid=imap_uid)
    return analyze_parsed_email(db, parsed_email)
