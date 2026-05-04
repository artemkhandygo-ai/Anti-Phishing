import os
from pathlib import Path

# Локальные дефолты для запуска без Docker.
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///./local_smoke_test.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("MAIL_IMAP_USERNAME", "test@example.com")
os.environ.setdefault("MAIL_IMAP_PASSWORD", "testpass")
os.environ.setdefault("MODEL_PATH", "data/models/phishguard_model.joblib")
os.environ.setdefault("WHITELIST_PATH", "data/config/whitelist_emails.txt")
os.environ.setdefault("URL_EXPANSION_ENABLED", "false")
os.environ.setdefault("URL_CONTENT_FETCH_ENABLED", "false")
os.environ.setdefault("DNS_CHECKS_ENABLED", "false")
os.environ.setdefault("TELEGRAM_NOTIFICATION_ASYNC", "false")
os.environ.setdefault("AUTO_MIGRATE", "false")

from app.db.migrate import run_migrations
from app.db.session import SessionLocal
from app.db.models import IncidentReason
from app.services.analysis_service import analyze_parsed_email


def print_result(title: str, parsed_email: dict) -> None:
    db = SessionLocal()
    try:
        incident = analyze_parsed_email(db, parsed_email)
        if incident is None:
            print(f"[{title}] письмо уже было обработано раньше")
            return
        reasons = db.query(IncidentReason).filter(IncidentReason.incident_id == incident.id).all()
        print("=" * 80)
        print(title)
        print(f"risk_level: {incident.risk_level}")
        print(f"risk_score: {incident.risk_score:.2f}")
        print(f"rule_score: {incident.rule_score:.2f}")
        print(f"ml_score: {incident.ml_score:.2f}")
        print("reasons:")
        for item in reasons:
            print(f" - [{item.severity}] {item.reason_code}: {item.reason_text}")
    finally:
        db.close()


def main() -> None:
    db_path = Path("local_smoke_test.db")
    if db_path.exists():
        db_path.unlink()

    run_migrations(retries=1, sleep_seconds=0.1)

    safe_email = {
        "imap_uid": "demo-1",
        "message_id": "<demo-safe@example.com>",
        "subject": "Встреча завтра",
        "from_email": "colleague@example.com",
        "from_name": "Коллега",
        "received_at": None,
        "text_body": "Привет. Напоминаю, что завтра у нас встреча в 11:00. Без вложений и без ссылок.",
        "html_body": None,
        "raw_headers": "From: colleague@example.com",
        "links": [],
        "attachments": [],
        "reply_to_email": "",
    }

    phishing_email = {
        "imap_uid": "demo-2",
        "message_id": "<demo-phish@example.com>",
        "subject": "СРОЧНО подтвердите аккаунт",
        "from_email": "security@example-support.com",
        "from_name": "Security Team",
        "received_at": None,
        "text_body": "Ваш аккаунт будет заблокирован. Срочно подтвердите пароль и перейдите по ссылке https://example.com/login",
        "html_body": None,
        "raw_headers": "From: security@example-support.com\nReply-To: verify@example-alerts.com",
        "links": ["https://example.com/login"],
        "attachments": [],
        "reply_to_email": "verify@example-alerts.com",
    }

    print_result("SAFE DEMO", safe_email)
    print_result("PHISHING DEMO", phishing_email)
    print("=" * 80)
    print("Smoke-test завершён.")
    print("Если ты увидел два обработанных письма с risk_level и reasons, значит базовый pipeline работает.")


if __name__ == "__main__":
    main()
