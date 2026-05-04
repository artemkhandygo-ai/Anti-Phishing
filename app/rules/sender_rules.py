def check_sender(features: dict) -> list[dict]:
    reasons = []
    if features.get("suspicious_sender", 0):
        reasons.append({
            "reason_code": "SUSPICIOUS_SENDER",
            "reason_text": "Адрес отправителя выглядит подозрительно или содержит нетипичные маркеры.",
            "severity": "medium",
            "score": 0.12,
        })

    auth_fail_count = int(features.get("auth_fail_count", 0) or 0)
    auth_pass_count = int(features.get("auth_pass_count", 0) or 0)
    explicit_auth_fail = auth_fail_count > 0
    auth_any_pass = auth_pass_count > 0

    if explicit_auth_fail:
        if auth_fail_count >= 3:
            reason_text = "Письмо не прошло SPF, DKIM и DMARC одновременно. Это сильный признак подмены отправителя или некорректной почтовой аутентификации."
            severity = "high"
            score = 0.38
        elif auth_fail_count == 2:
            reason_text = "Письмо не прошло две базовые почтовые проверки аутентификации. Это сильный инфраструктурный риск."
            severity = "high"
            score = 0.3
        elif auth_any_pass:
            reason_text = "Одна из базовых почтовых проверок аутентификации не пройдена, хотя другие признаки аутентификации частично успешны."
            severity = "medium"
            score = 0.14
        else:
            reason_text = "Письмо явно не прошло одну из базовых почтовых проверок аутентификации."
            severity = "medium"
            score = 0.2
        reasons.append({
            "reason_code": "AUTH_FAIL",
            "reason_text": reason_text,
            "severity": severity,
            "score": score,
        })
    if features.get("from_reply_to_mismatch", 0):
        reasons.append({
            "reason_code": "FROM_REPLY_MISMATCH",
            "reason_text": "Адрес Reply-To не совпадает с доменом отправителя. Это может указывать на подмену цепочки ответа.",
            "severity": "high",
            "score": 0.18,
        })
    if not features.get("sender_domain_has_mx", 0):
        reasons.append({
            "reason_code": "NO_MX_RECORD",
            "reason_text": "У домена отправителя не найдены MX-записи, что нетипично для реальной почтовой инфраструктуры.",
            "severity": "medium",
            "score": 0.12,
        })
    if not features.get("sender_domain_has_spf_dns", 0):
        reasons.append({
            "reason_code": "NO_SPF_POLICY",
            "reason_text": "У домена отправителя не найдена SPF-политика.",
            "severity": "medium",
            "score": 0.08,
        })
    if not features.get("sender_domain_has_dmarc_dns", 0):
        reasons.append({
            "reason_code": "NO_DMARC_POLICY",
            "reason_text": "У домена отправителя не найдена DMARC-политика.",
            "severity": "low",
            "score": 0.05,
        })
    if features.get("sender_domain_punycode", 0) or features.get("reply_domain_punycode", 0):
        reasons.append({
            "reason_code": "PUNYCODE_DOMAIN",
            "reason_text": "Домен использует punycode или визуально нестандартное имя.",
            "severity": "high",
            "score": 0.18,
        })
    if features.get("lookalike_reply_domain", 0):
        reasons.append({
            "reason_code": "LOOKALIKE_REPLY_DOMAIN",
            "reason_text": "Reply-To похож на домен отправителя, но не совпадает с ним. Это типичный признак маскировки.",
            "severity": "high",
            "score": 0.2,
        })

    sender_infra_is_suspicious = any([
        explicit_auth_fail,
        features.get("from_reply_to_mismatch", 0),
        features.get("lookalike_reply_domain", 0),
        features.get("sender_domain_punycode", 0),
        not features.get("sender_domain_has_spf_dns", 0),
        not features.get("sender_domain_has_dmarc_dns", 0),
    ])
    suppress_infra_mismatch = auth_any_pass or features.get("sender_ip_matches_spf", 0)

    if features.get("sender_ip_mx_comparable", 0) and features.get("sender_ip_matches_domain", 0) and sender_infra_is_suspicious:
        reasons.append({
            "reason_code": "RECEIVED_IP_MATCHES_MX",
            "reason_text": "IP-адрес отправляющего сервера из заголовка Received совпадает с IP почтовой инфраструктуры домена отправителя.",
            "severity": "low",
            "score": 0.02,
        })
    elif features.get("sender_ip_mx_comparable", 0) and not features.get("sender_ip_matches_domain", 0) and sender_infra_is_suspicious and not suppress_infra_mismatch:
        reasons.append({
            "reason_code": "RECEIVED_IP_MX_MISMATCH",
            "reason_text": "IP-адрес отправляющего сервера из заголовка Received не совпадает с IP почтовой инфраструктуры домена отправителя, а других признаков легитимной почтовой отправки не видно.",
            "severity": "medium",
            "score": 0.05,
        })

    if (
        features.get("sender_ip_infrastructure_comparable", 0)
        and not features.get("sender_ip_matches_infrastructure", 0)
        and sender_infra_is_suspicious
        and not suppress_infra_mismatch
    ):
        reasons.append({
            "reason_code": "RECEIVED_IP_NOT_IN_INFRASTRUCTURE",
            "reason_text": "IP-адрес отправляющего сервера не совпадает ни с MX, ни с A-записью домена и не входит в базовую SPF-инфраструктуру отправителя.",
            "severity": "medium",
            "score": 0.06,
        })
    return reasons
