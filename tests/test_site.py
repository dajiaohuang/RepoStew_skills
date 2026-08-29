import json
import unittest
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


class SiteParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.links = []
        self.scripts = []
        self.html_attributes = {}
        self.buttons = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "html":
            self.html_attributes = attributes
        if "id" in attributes:
            self.ids.add(attributes["id"])
        if tag in {"a", "link"} and (attributes.get("href")):
            self.links.append(attributes["href"])
        if tag == "script" and attributes.get("src"):
            self.scripts.append(attributes["src"])
        if tag == "button":
            self.buttons.append(attributes)


class SiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (DOCS / "index.html").read_text(encoding="utf-8")
        cls.css = (DOCS / "styles.css").read_text(encoding="utf-8")
        cls.javascript = (DOCS / "app.js").read_text(encoding="utf-8")
        cls.parser = SiteParser()
        cls.parser.feed(cls.html)

    def test_chinese_is_the_default_language(self):
        self.assertEqual(self.parser.html_attributes.get("lang"), "zh-CN")
        self.assertEqual(self.parser.html_attributes.get("data-language"), "zh")
        self.assertIn("补丁只是开始", self.html)

    def test_navigation_targets_exist(self):
        fragment_links = [link[1:] for link in self.parser.links if link.startswith("#")]
        self.assertTrue(fragment_links)
        self.assertFalse(set(fragment_links) - self.parser.ids)

    def test_all_local_assets_exist(self):
        local_paths = []
        for reference in self.parser.links + self.parser.scripts:
            parsed = urlparse(reference)
            if parsed.scheme or reference.startswith(('#', '../')):
                continue
            local_paths.append(DOCS / parsed.path)
        missing = [str(path.relative_to(ROOT)) for path in local_paths if not path.exists()]
        self.assertEqual(missing, [])

    def test_interactive_controls_are_labeled(self):
        self.assertGreaterEqual(len(self.parser.buttons), 9)
        for attributes in self.parser.buttons:
            has_name = "aria-label" in attributes or "data-i18n" in attributes or "data-step" in attributes
            self.assertTrue(has_name, attributes)

    def test_site_has_no_remote_runtime_dependency(self):
        self.assertNotIn("https://", " ".join(self.parser.scripts))
        self.assertNotIn("@import url", self.css)
        self.assertIn("prefers-reduced-motion", self.css)

    def test_manifest_and_sitemap_are_valid(self):
        manifest = json.loads((DOCS / "site.webmanifest").read_text(encoding="utf-8"))
        self.assertEqual(manifest["start_url"], "/RepoStew_skills/")
        ET.parse(DOCS / "sitemap.xml")


if __name__ == "__main__":
    unittest.main()
