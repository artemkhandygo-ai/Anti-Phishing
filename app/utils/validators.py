from urllib.parse import urlparse

SHORTENER_DOMAINS = {
    "bit.ly", "tinyurl.com", "t.co", "goo.gl", "ow.ly", "cutt.ly", "is.gd", "buff.ly",
    "clck.ru", "lnkd.in", "rebrand.ly", "tiny.one", "rb.gy"
}


def get_domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lower()
    except Exception:
        return ""


def is_shortened_url(url: str) -> bool:
    domain = get_domain(url)
    return domain in SHORTENER_DOMAINS
