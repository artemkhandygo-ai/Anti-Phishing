import re
from bs4 import BeautifulSoup

URL_RE = re.compile(r'https?://[^\s<>"\']+')
TRAILING_URL_CHARS = ".,;:!?)]}»”’\"'"


def clean_url(url: str | None) -> str:
    """Remove punctuation/brackets that often stick to URLs in plain text."""
    return (url or "").strip().rstrip(TRAILING_URL_CHARS)


def extract_links(text: str | None, html: str | None) -> list[str]:
    links: list[str] = []
    if text:
        links.extend(clean_url(item) for item in URL_RE.findall(text))
    if html:
        soup = BeautifulSoup(html, "lxml")
        for tag in soup.find_all("a", href=True):
            links.append(clean_url(tag["href"]))
    deduped = []
    seen = set()
    for link in links:
        if link and link not in seen:
            seen.add(link)
            deduped.append(link)
    return deduped
