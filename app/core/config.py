from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = "Anti-Phishing"
    APP_ENV: str = "development"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    DATABASE_URL: str
    REDIS_URL: str
    AUTO_MIGRATE: bool = True

    MAIL_IMAP_HOST: str = "imap.mail.ru"
    MAIL_IMAP_PORT: int = 993
    MAIL_IMAP_USERNAME: str
    MAIL_IMAP_PASSWORD: str
    MAIL_IMAP_FOLDER: str = "INBOX"

    TELEGRAM_BOT_TOKEN: str | None = None
    TELEGRAM_CHAT_ID: str | None = None
    TELEGRAM_FEEDBACK_POLL_ENABLED: bool = True
    TELEGRAM_FEEDBACK_POLL_INTERVAL_SECONDS: int = 20
    TELEGRAM_API_TIMEOUT_SECONDS: int = 15
    TELEGRAM_API_RETRIES: int = 2
    TELEGRAM_API_RETRY_SLEEP_SECONDS: float = 1.0
    TELEGRAM_NOTIFICATION_ASYNC: bool = True

    MODEL_PATH: str = "/app/data/models/phishguard_model.joblib"
    VECTORIZER_PATH: str = "/app/data/models/phishguard_vectorizer.joblib"
    SCALER_PATH: str = "/app/data/models/phishguard_tabular_scaler.joblib"

    TEXT_FIELD_LIMIT: int = 30000
    POLL_CRON_MINUTES: int = 5

    MAIL_POLL_ENABLED: bool = True
    MAIL_POLL_INTERVAL_SECONDS: int = 60
    MAIL_FETCH_LIMIT: int = 20
    MAIL_INITIAL_BOOTSTRAP_LIMIT: int = 5
    MAIL_POLL_LOCK_TTL_SECONDS: int = 300
    TELEGRAM_POLL_LOCK_TTL_SECONDS: int = 120
    NOTIFICATION_TASK_LOCK_TTL_SECONDS: int = 120

    NOTIFY_ON_ALL_EMAILS: bool = True
    NOTIFY_ONLY_HIGH_RISK: bool = False
    TELEGRAM_INCLUDE_FULL_TEXT: bool = True
    TELEGRAM_FULL_TEXT_LIMIT: int = 3500

    WHITELIST_PATH: str = "/app/data/config/whitelist_emails.txt"

    DNS_CHECKS_ENABLED: bool = True
    DOMAIN_SECURITY_RESOLVERS: str = "1.1.1.1,8.8.8.8"
    URL_EXPANSION_ENABLED: bool = True
    URL_CONTENT_FETCH_ENABLED: bool = True
    URL_REQUEST_TIMEOUT_SECONDS: int = 12
    URL_REQUEST_CONNECT_TIMEOUT_SECONDS: int = 5
    URL_REQUEST_RETRIES: int = 1
    URL_REQUEST_RETRY_SLEEP_SECONDS: float = 1.0
    URL_MAX_CONTENT_CHARS: int = 18000
    URL_DEEP_ANALYSIS_ENABLED: bool = True
    URL_MAX_INSPECTED_LINKS_PER_EMAIL: int = 3
    URL_MAX_DEEP_FETCH_LINKS_PER_EMAIL: int = 1


settings = Settings()
