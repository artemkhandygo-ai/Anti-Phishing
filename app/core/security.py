from hashlib import sha256


def hash_text(value: str) -> str:
    return sha256(value.encode("utf-8", errors="ignore")).hexdigest()
