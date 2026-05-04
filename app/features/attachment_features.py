DANGEROUS_EXTENSIONS = {".exe", ".js", ".vbs", ".scr", ".bat", ".cmd", ".ps1", ".docm", ".xlsm", ".zip", ".rar"}


def extract_attachment_features(attachments: list[dict]) -> dict:
    ext_list = [att.get("extension", "").lower() for att in attachments]
    dangerous_count = sum(1 for ext in ext_list if ext in DANGEROUS_EXTENSIONS)
    return {
        "attachments_count": len(attachments),
        "dangerous_attachments_count": dangerous_count,
    }
