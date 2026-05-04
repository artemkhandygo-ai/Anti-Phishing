import email
import imaplib
import logging
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


class IMAPClient:
    def __init__(self) -> None:
        self.host = settings.MAIL_IMAP_HOST
        self.port = settings.MAIL_IMAP_PORT
        self.username = settings.MAIL_IMAP_USERNAME
        self.password = settings.MAIL_IMAP_PASSWORD
        self.folder = settings.MAIL_IMAP_FOLDER

    def _connect(self) -> imaplib.IMAP4_SSL:
        logger.info("Connecting to IMAP host %s", self.host)
        client = imaplib.IMAP4_SSL(self.host, self.port)
        client.login(self.username, self.password)
        client.select(self.folder)
        return client

    def _fetch_uid_list(self, client: imaplib.IMAP4_SSL, criteria: str = "ALL") -> list[bytes]:
        status, data = client.uid("search", None, criteria)
        if status != "OK" or not data or not data[0]:
            return []
        return data[0].split()

    def _fetch_messages_by_uids(self, client: imaplib.IMAP4_SSL, uid_list: list[bytes]) -> list[dict[str, Any]]:
        results = []
        for uid in uid_list:
            status, msg_data = client.uid("fetch", uid, "(RFC822)")
            if status != "OK" or not msg_data or msg_data[0] is None:
                continue
            raw_bytes = msg_data[0][1]
            message = email.message_from_bytes(raw_bytes)
            results.append({
                "imap_uid": uid.decode(),
                "raw_bytes": raw_bytes,
                "message": message,
            })
        return results

    def fetch_recent(self, limit: int = 5) -> list[dict[str, Any]]:
        client = self._connect()
        try:
            uids = self._fetch_uid_list(client, "ALL")
            if not uids:
                return []
            selected = uids[-limit:]
            return self._fetch_messages_by_uids(client, selected)
        finally:
            try:
                client.close()
            except Exception:
                pass
            client.logout()

    def fetch_since_uid(self, last_uid: int | None, limit: int = 20) -> list[dict[str, Any]]:
        client = self._connect()
        try:
            uids = self._fetch_uid_list(client, "ALL")
            if not uids:
                return []
            numeric_uids = []
            for uid in uids:
                try:
                    numeric_uids.append((int(uid.decode()), uid))
                except ValueError:
                    continue
            if last_uid is None:
                selected = [uid for _, uid in numeric_uids[-limit:]]
            else:
                newer = [uid for numeric, uid in numeric_uids if numeric > last_uid]
                selected = newer[:limit]
            if not selected:
                return []
            return self._fetch_messages_by_uids(client, selected)
        finally:
            try:
                client.close()
            except Exception:
                pass
            client.logout()
