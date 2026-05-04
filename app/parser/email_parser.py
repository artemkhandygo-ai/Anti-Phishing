from datetime import datetime
from email.message import Message
from email.utils import parsedate_to_datetime, parseaddr

from app.mail.mail_utils import decode_mime_header
from app.parser.attachment_utils import extract_attachments
from app.parser.html_utils import html_to_text
from app.parser.link_extractor import extract_links


def _extract_bodies(message: Message) -> tuple[str, str]:
    text_body = ""
    html_body = ""
    if message.is_multipart():
        for part in message.walk():
            ctype = part.get_content_type()
            disp = str(part.get("Content-Disposition", ""))
            if "attachment" in disp.lower():
                continue
            try:
                payload = part.get_payload(decode=True)
                charset = part.get_content_charset() or "utf-8"
                decoded = payload.decode(charset, errors="ignore") if payload else ""
            except Exception:
                decoded = ""
            if ctype == "text/plain" and not text_body:
                text_body = decoded
            elif ctype == "text/html" and not html_body:
                html_body = decoded
    else:
        payload = message.get_payload(decode=True)
        charset = message.get_content_charset() or "utf-8"
        decoded = payload.decode(charset, errors="ignore") if payload else ""
        if message.get_content_type() == "text/html":
            html_body = decoded
        else:
            text_body = decoded
    if not text_body and html_body:
        text_body = html_to_text(html_body)
    return text_body, html_body


def parse_message(message: Message, imap_uid: str | None = None) -> dict:
    text_body, html_body = _extract_bodies(message)
    links = extract_links(text_body, html_body)
    raw_from = decode_mime_header(message.get("From"))
    from_name, from_email = parseaddr(raw_from)
    reply_to_raw = decode_mime_header(message.get("Reply-To"))
    _, reply_to_email = parseaddr(reply_to_raw)
    return_path_raw = decode_mime_header(message.get("Return-Path"))
    _, return_path_email = parseaddr(return_path_raw)
    subject = decode_mime_header(message.get("Subject"))
    date_header = message.get("Date")
    received_at = None
    if date_header:
        try:
            received_at = parsedate_to_datetime(date_header).replace(tzinfo=None)
        except Exception:
            received_at = None
    return {
        "imap_uid": imap_uid,
        "message_id": message.get("Message-ID"),
        "subject": subject,
        "from_raw": raw_from,
        "from_email": (from_email or raw_from or "").strip().lower(),
        "from_name": from_name or raw_from,
        "reply_to_email": (reply_to_email or "").strip().lower(),
        "return_path_email": (return_path_email or "").strip().lower(),
        "received_at": received_at or datetime.utcnow(),
        "text_body": text_body,
        "html_body": html_body,
        "raw_headers": "\n".join([f"{k}: {v}" for k, v in message.items()]),
        "links": links,
        "attachments": extract_attachments(message),
    }
