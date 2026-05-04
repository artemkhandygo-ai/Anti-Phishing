from email.message import Message
from pathlib import Path


def extract_attachments(message: Message) -> list[dict]:
    attachments: list[dict] = []
    for part in message.walk():
        filename = part.get_filename()
        if not filename:
            continue
        payload = part.get_payload(decode=True) or b""
        attachments.append(
            {
                "filename": filename,
                "content_type": part.get_content_type(),
                "size": len(payload),
                "extension": Path(filename).suffix.lower(),
            }
        )
    return attachments
