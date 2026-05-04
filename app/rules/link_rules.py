def check_links(features: dict) -> list[dict]:
    reasons = []
    if features.get("shortened_links_count", 0) > 0:
        reasons.append({
            "reason_code": "SHORTENED_LINK",
            "reason_text": "В письме обнаружена сокращённая ссылка. Такие ссылки часто используют для маскировки конечного адреса.",
            "severity": "high",
            "score": 0.2,
        })
    if features.get("links_count", 0) >= 3:
        reasons.append({
            "reason_code": "MANY_LINKS",
            "reason_text": "В письме обнаружено необычно много ссылок.",
            "severity": "medium",
            "score": 0.1,
        })
    if features.get("suspicious_url_keywords_count", 0) > 0:
        reasons.append({
            "reason_code": "URL_LOGIN_KEYWORDS",
            "reason_text": "В ссылке обнаружены слова, характерные для страниц входа, подтверждения или проверки аккаунта.",
            "severity": "medium",
            "score": 0.14,
        })
    if features.get("ip_url_count", 0) > 0:
        reasons.append({
            "reason_code": "IP_URL",
            "reason_text": "В письме есть ссылка на IP-адрес вместо обычного доменного имени.",
            "severity": "high",
            "score": 0.18,
        })
    if features.get("resolved_domain_changed_count", 0) > 0:
        reasons.append({
            "reason_code": "REDIRECTED_DOMAIN",
            "reason_text": "Ссылка после перехода ведёт на другой домен, чем казалось изначально.",
            "severity": "high",
            "score": 0.16,
        })
    if features.get("login_page_hits", 0) > 0:
        reasons.append({
            "reason_code": "LOGIN_PAGE_LINK",
            "reason_text": "Открытая по ссылке страница похожа на форму входа или подтверждения учётной записи.",
            "severity": "high",
            "score": 0.2,
        })
    if features.get("external_form_action_hits", 0) > 0:
        reasons.append({
            "reason_code": "EXTERNAL_FORM_ACTION",
            "reason_text": "На целевой странице форма отправляет данные на внешний домен, отличный от открытой страницы.",
            "severity": "high",
            "score": 0.16,
        })
    if features.get("brand_mismatch_hits", 0) > 0 and features.get("high_conf_brand_hits", 0) > 0:
        reasons.append({
            "reason_code": "BRAND_MISMATCH_PAGE",
            "reason_text": "Содержимое страницы уверенно имитирует известный бренд, но домен ссылки ему не соответствует.",
            "severity": "high",
            "score": 0.2,
        })
    if features.get("credential_collection_hits", 0) > 0:
        reasons.append({
            "reason_code": "CREDENTIAL_COLLECTION_PAGE",
            "reason_text": "По ссылке открывается страница, которая собирает учётные данные пользователя.",
            "severity": "high",
            "score": 0.18,
        })
    if features.get("payment_collection_hits", 0) > 0:
        reasons.append({
            "reason_code": "PAYMENT_COLLECTION_PAGE",
            "reason_text": "По ссылке открывается страница, которая собирает платёжные данные или реквизиты.",
            "severity": "high",
            "score": 0.18,
        })
    if features.get("sensitive_form_hits", 0) > 0 and features.get("credential_collection_hits", 0) == 0 and features.get("payment_collection_hits", 0) == 0:
        reasons.append({
            "reason_code": "SENSITIVE_FORM_PAGE",
            "reason_text": "По ссылке открывается страница, которая запрашивает чувствительные данные или коды подтверждения.",
            "severity": "medium",
            "score": 0.12,
        })
    if features.get("non_https_links_count", 0) > 0:
        reasons.append({
            "reason_code": "NON_HTTPS_LINK",
            "reason_text": "В письме есть ссылка без HTTPS.",
            "severity": "medium",
            "score": 0.08,
        })
    return reasons
