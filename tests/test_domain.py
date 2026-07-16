import unittest

from yt_dlp.extractor import gen_extractor_classes

from flow.domain.formatting import format_bytes, format_time
from flow.domain.sites import PLATFORM_DOMAINS, platform_name, supported_platforms


class FormattingTests(unittest.TestCase):
    def test_time_under_one_hour(self):
        self.assertEqual(format_time(65), "01:05")

    def test_time_over_one_hour(self):
        self.assertEqual(format_time(3665), "01:01:05")

    def test_unknown_values(self):
        self.assertEqual(format_time(None), "--:--")
        self.assertEqual(format_bytes(None), "—")


class PlatformTests(unittest.TestCase):
    def test_known_subdomain(self):
        self.assertEqual(platform_name("https://m.youtube.com/watch?v=1"), "YouTube")

    def test_domain_substring_is_not_a_match(self):
        self.assertEqual(platform_name("https://notx.com/video"), "Sitio web")

    def test_thirty_additional_platforms_are_recognized(self):
        self.assertEqual(len(supported_platforms()), 35)
        self.assertEqual(len(set(supported_platforms())), 35)
        self.assertEqual(len(PLATFORM_DOMAINS), 35)
        self.assertEqual(
            set(supported_platforms()),
            {name for name, _ in PLATFORM_DOMAINS},
        )
        for expected, domains in PLATFORM_DOMAINS:
            with self.subTest(platform=expected):
                self.assertEqual(platform_name(f"https://www.{domains[0]}/video/1"), expected)

    def test_short_domains_and_mobile_subdomains_are_recognized(self):
        cases = {
            "https://dai.ly/x1": "Dailymotion",
            "https://pin.it/abc": "Pinterest",
            "https://m.weibo.cn/detail/1": "Weibo",
            "https://flic.kr/p/abc": "Flickr",
        }
        for url, expected in cases.items():
            with self.subTest(url=url):
                self.assertEqual(platform_name(url), expected)

    def test_ytdlp_includes_extractors_for_all_added_platforms(self):
        available = {extractor.__name__ for extractor in gen_extractor_classes()}
        required = {
            "VimeoIE", "DailymotionIE", "TwitchVodIE", "RedditIE",
            "PinterestIE", "SnapchatSpotlightIE", "SoundcloudIE", "BandcampIE",
            "MixcloudIE", "RumbleIE", "BiliBiliIE", "VKIE",
            "OdnoklassnikiIE", "TumblrIE", "FlickrIE", "ImgurIE",
            "StreamableIE", "KickClipIE", "BlueskyIE", "LinkedInIE",
            "LikeeIE", "TelegramEmbedIE", "BitChuteIE", "LBRYIE",
            "YouNowChannelIE", "GabIE", "TruthIE", "WeiboIE", "NineGagIE",
            "CoubIE",
        }
        self.assertEqual(required - available, set())


if __name__ == "__main__":
    unittest.main()
