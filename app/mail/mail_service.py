from app.mail.imap_client import IMAPClient


class MailService:
    def __init__(self) -> None:
        self.client = IMAPClient()

    def fetch_initial_batch(self, limit: int = 5):
        return self.client.fetch_recent(limit=limit)

    def fetch_new_since(self, last_uid: int | None, limit: int = 20):
        return self.client.fetch_since_uid(last_uid=last_uid, limit=limit)
