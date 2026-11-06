from html import unescape
import re
import unittest
from urllib.parse import parse_qs, urlsplit

from category_harness import ROUTES, Theme, prepare, quoted_type, source


def links(markup):
    return {
        unescape(re.sub(r"<[^>]+>", "", label)).strip().removesuffix(" ↗"): unescape(url)
        for url, label in re.findall(r'<a\b[^>]*href="([^"]+)"[^>]*>(.*?)</a>', markup, re.S)
    }


class DepartmentNavigationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        env = Theme().env
        cls.header = env.from_string(prepare(source("sections/ff-header.liquid")))
        cls.footer = env.from_string(prepare(source("sections/ff-footer.liquid")))

    def render(self, template, collections=None, **settings):
        return template.render(
            section={"settings": {"guide_url": "", "menu": "", "shop_menu": "", "info_menu": "", **settings}},
            routes=dict(ROUTES, search_url="/en/search", cart_url="/cart"),
            collections=collections or {}, shop={"name": "FretFuel"},
            search={"terms": ""}, cart={"item_count": 0},
        )

    def types(self, href):
        parsed = urlsplit(href)
        self.assertEqual(parsed.path, "/en/search")
        query = parse_qs(parsed.query)
        self.assertEqual(query["type"], ["product"])
        return {quoted_type(term) for term in query["q"][0].split(" OR ")}

    def test_default_department_links_filter_their_own_types(self):
        markup = self.render(self.header)
        departments = links(re.search(r'<nav class="department-nav".*?</nav>', markup, re.S)[0])
        mega = links(re.search(r'<nav id="mega-menu".*?</nav>', markup, re.S)[0])
        footer = links(self.render(self.footer))
        groups = {
            "Tuners": {"Guitar tuners", "Bass tuners", "Classical tuners"},
            "Bridges & tailpieces": {"Bridge", "Bridges", "Fixed bridges", "Tremolo bridges", "Tailpieces", "Vibrato tailpieces"},
            "Pickups": {"Pickups"},
            "Electronics": {"Electronics"},
            "Pickguards": {"Pickguards"},
            "Hardware & small parts": {"Hardware", "Saddles", "Knobs", "Screws"},
        }
        for label, expected in groups.items():
            with self.subTest(label=label):
                self.assertEqual(self.types(departments[label]), expected)
                self.assertEqual(mega[label], departments[label])
                self.assertEqual(footer[label], departments[label])

        children = {
            "Guitar tuners": "Guitar tuners", "Bass tuners": "Bass tuners",
            "Tremolo bridges": "Tremolo bridges", "Tailpieces": "Tailpieces",
            "Shop pickups": "Pickups", "Shop electronics": "Electronics",
            "Shop pickguards": "Pickguards", "Saddles": "Saddles", "Control knobs": "Knobs",
        }
        for label, expected in children.items():
            with self.subTest(label=label):
                self.assertEqual(self.types(mega[label]), {expected})

        self.assertEqual(mega["Browse all parts"], "/collections/all")
        self.assertEqual(footer["All replacement parts"], "/collections/all")

    def test_configured_collections_take_priority_at_their_own_level(self):
        menu_links = links(self.render(self.header, {
            "tuners": {"url": "/collections/curated-tuners"},
            "guitar-tuners": {"url": "/collections/curated-guitar-tuners"},
            "bass-tuners": {"url": ""},
        }))
        self.assertEqual(menu_links["Tuners"], "/collections/curated-tuners")
        self.assertEqual(menu_links["Guitar tuners"], "/collections/curated-guitar-tuners")
        self.assertEqual(self.types(menu_links["Bass tuners"]), {"Bass tuners"})

    def test_selected_shopify_menu_keeps_its_own_links(self):
        menu = {"links": [{"title": "Custom department", "url": "/collections/custom", "links": [
            {"title": "Custom part", "url": "/collections/custom-part"},
        ]}]}
        markup = self.render(self.header, menu=menu)
        menu_links = links(markup)
        self.assertEqual(menu_links["Custom department"], "/collections/custom")
        self.assertEqual(menu_links["Custom part"], "/collections/custom-part")
        self.assertNotIn("Tuners", menu_links)


if __name__ == "__main__":
    unittest.main()
