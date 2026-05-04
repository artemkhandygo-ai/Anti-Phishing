import re

from app.network_checks.domain_security import evaluate_trust_chain


def _status(headers: str, key: str) -> str:
    if f"{key}=pass" in headers:
        return "pass"
    if f"{key}=fail" in headers or f"{key}=softfail" in headers:
        return "fail"
    return "unknown"


def extract_header_features(raw_headers: str | None, from_email: str | None, reply_to_email: str | None = None) -> dict:
    headers = (raw_headers or "").lower()
    sender = (from_email or "").lower()

    spf_status = _status(headers, "spf")
    dkim_status = _status(headers, "dkim")
    dmarc_status = _status(headers, "dmarc")

    suspicious_sender = int(bool(re.search(r"(support|security|verify|update|billing|payroll)", sender)))
    trust_chain = evaluate_trust_chain(raw_headers, from_email, reply_to_email)
    spf_pass = int(spf_status == "pass")
    dkim_pass = int(dkim_status == "pass")
    dmarc_pass = int(dmarc_status == "pass")
    spf_fail = int(spf_status == "fail")
    dkim_fail = int(dkim_status == "fail")
    dmarc_fail = int(dmarc_status == "fail")

    return {
        "spf_status": spf_status,
        "dkim_status": dkim_status,
        "dmarc_status": dmarc_status,
        "spf_pass": spf_pass,
        "dkim_pass": dkim_pass,
        "dmarc_pass": dmarc_pass,
        "spf_fail": spf_fail,
        "dkim_fail": dkim_fail,
        "dmarc_fail": dmarc_fail,
        "auth_pass_count": spf_pass + dkim_pass + dmarc_pass,
        "auth_fail_count": spf_fail + dkim_fail + dmarc_fail,
        "suspicious_sender": suspicious_sender,
        **trust_chain,
    }
