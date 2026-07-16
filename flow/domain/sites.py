from urllib.parse import urlparse


PLATFORM_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "Principales",
        ("YouTube", "TikTok", "Facebook", "Instagram", "X / Twitter"),
    ),
    (
        "Video y directos",
        (
            "Vimeo",
            "Dailymotion",
            "Twitch",
            "Rumble",
            "Bilibili",
            "Streamable",
            "Kick",
            "BitChute",
            "Odysee",
            "YouNow",
            "Coub",
        ),
    ),
    (
        "Sociales y comunidades",
        (
            "Reddit",
            "Pinterest",
            "Snapchat",
            "VK",
            "OK.ru",
            "Tumblr",
            "Flickr",
            "Imgur",
            "Bluesky",
            "LinkedIn",
            "Likee",
            "Telegram",
            "Gab",
            "Truth Social",
            "Weibo",
            "9GAG",
        ),
    ),
    (
        "Audio",
        ("SoundCloud", "Bandcamp", "Mixcloud"),
    ),
)


PLATFORM_DOMAINS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("YouTube", ("youtube.com", "youtu.be")),
    ("X / Twitter", ("x.com", "twitter.com")),
    ("TikTok", ("tiktok.com",)),
    ("Instagram", ("instagram.com",)),
    ("Facebook", ("facebook.com", "fb.watch")),
    ("Vimeo", ("vimeo.com",)),
    ("Dailymotion", ("dailymotion.com", "dai.ly")),
    ("Twitch", ("twitch.tv",)),
    ("Rumble", ("rumble.com",)),
    ("Bilibili", ("bilibili.com", "b23.tv")),
    ("Streamable", ("streamable.com",)),
    ("Kick", ("kick.com",)),
    ("BitChute", ("bitchute.com",)),
    ("Odysee", ("odysee.com", "lbry.tv")),
    ("YouNow", ("younow.com",)),
    ("Coub", ("coub.com",)),
    ("Reddit", ("reddit.com", "redd.it")),
    ("Pinterest", ("pinterest.com", "pin.it")),
    ("Snapchat", ("snapchat.com",)),
    ("VK", ("vk.com", "vkvideo.ru")),
    ("OK.ru", ("ok.ru", "odnoklassniki.ru")),
    ("Tumblr", ("tumblr.com",)),
    ("Flickr", ("flickr.com", "flic.kr")),
    ("Imgur", ("imgur.com",)),
    ("Bluesky", ("bsky.app",)),
    ("LinkedIn", ("linkedin.com",)),
    ("Likee", ("likee.video", "likee.com")),
    ("Telegram", ("t.me", "telegram.me")),
    ("Gab", ("gab.com",)),
    ("Truth Social", ("truthsocial.com",)),
    ("Weibo", ("weibo.com", "weibo.cn")),
    ("9GAG", ("9gag.com",)),
    ("SoundCloud", ("soundcloud.com",)),
    ("Bandcamp", ("bandcamp.com",)),
    ("Mixcloud", ("mixcloud.com",)),
)


def _is_domain(host: str, domain: str) -> bool:
    return host == domain or host.endswith("." + domain)


def supported_platforms() -> tuple[str, ...]:
    return tuple(name for _, names in PLATFORM_GROUPS for name in names)


def platform_name(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    for name, domains in PLATFORM_DOMAINS:
        if any(_is_domain(host, domain) for domain in domains):
            return name
    return "Sitio web"
