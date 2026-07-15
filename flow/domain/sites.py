from urllib.parse import urlparse


def _is_domain(host: str, domain: str) -> bool:
    return host == domain or host.endswith("." + domain)


def platform_name(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    if _is_domain(host, "youtube.com") or _is_domain(host, "youtu.be"):
        return "YouTube"
    if _is_domain(host, "x.com") or _is_domain(host, "twitter.com"):
        return "X / Twitter"
    if _is_domain(host, "tiktok.com"):
        return "TikTok"
    if _is_domain(host, "instagram.com"):
        return "Instagram"
    if _is_domain(host, "facebook.com") or _is_domain(host, "fb.watch"):
        return "Facebook"
    return "Sitio web"
