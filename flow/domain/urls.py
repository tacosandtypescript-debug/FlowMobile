from __future__ import annotations

import re
from urllib.parse import urlparse


WEB_URL_PATTERN = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)
TRAILING_PUNCTUATION = ".,;:!?)]}>"


def is_web_url(value: str) -> bool:
    try:
        parsed = urlparse(value.strip())
    except ValueError:
        return False
    return parsed.scheme.lower() in {"http", "https"} and bool(parsed.hostname)


def extract_web_urls(text: str, limit: int = 50) -> list[str]:
    urls: list[str] = []
    for match in WEB_URL_PATTERN.finditer(text[:32_768]):
        candidate = match.group(0).rstrip(TRAILING_PUNCTUATION)
        if is_web_url(candidate) and candidate not in urls:
            urls.append(candidate)
        if len(urls) >= limit:
            break
    return urls
