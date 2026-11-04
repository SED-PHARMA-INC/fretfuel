import copy
import html
from html.parser import HTMLParser
import random
import re
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit
from urllib.request import urlopen

from category_harness import ROOT, ROUTES, TYPES, Theme, catalog, handler, product, quoted_type

BASE = "c0f70e59f2275968afaa05fe44be6575db19c6bf"


def cards(markup):
    return [html.unescape(value) for value in re.findall(r'<a class="category-card" href="([^"]*)"', markup)]


def query(url):
    return parse_qs(urlsplit(url).query)["q"][0]


class DOM(HTMLParser):
    def __init__(self, markup):
        super().__init__(convert_charrefs=True)
        self.events = []
        self.tags = []
        self.feed(markup)

    def handle_starttag(self, tag, attrs):
        self.events.append((tag, tuple(attrs)))
        self.tags.append((tag, dict(attrs)))

    def handle_endtag(self, tag):
        self.events.append(("/" + tag,))

    def handle_data(self, data):
        if data.strip():
            self.events.append(("text", data.strip()))


class UnitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.theme = Theme()

    def test_nine_distinct_category_links(self):
        links = cards(self.theme.render_home())
        self.assertEqual(len(links), 9)
        self.assertEqual(len(set(links)), 9)
        for link, kind in zip(links, TYPES):
            with self.subTest(kind=kind):
                self.assertEqual(urlsplit(link).path, "/search")
                self.assertEqual(parse_qs(urlsplit(link).query)["type"], ["product"])
                self.assertEqual(quoted_type(query(link)), kind)

    def test_configured_collection_has_priority(self):
        blocks = self.theme.blocks()
        for block, kind in zip(blocks, TYPES):
            block["settings"]["collection"] = {"url": "/collections/custom-" + kind.split()[0].lower()}
        links = cards(self.theme.render_home(blocks))
        self.assertEqual(links, [block["settings"]["collection"]["url"] for block in blocks])

    def test_missing_and_deleted_collections_use_type(self):
        for setting in (None, "", "deleted-collection", {}, {"url": ""}):
            with self.subTest(setting=setting):
                blocks = self.theme.blocks()
                blocks[0]["settings"]["collection"] = setting
                self.assertEqual(quoted_type(query(cards(self.theme.render_home(blocks))[0])), TYPES[0])

    def test_explicit_product_type_overrides_illustration(self):
        blocks = self.theme.blocks()
        blocks[0]["settings"]["product_type"] = "Custom tuner"
        self.assertEqual(quoted_type(query(cards(self.theme.render_home(blocks))[0])), "Custom tuner")

    def test_default_specific_collection_handles(self):
        blocks = self.theme.blocks()
        self.assertEqual(blocks[0]["settings"]["collection"], "guitar-tuners")
        self.assertEqual(blocks[2]["settings"]["collection"], "tremolo-bridges")

    def test_category_name_count_and_cards(self):
        for kind in TYPES:
            with self.subTest(kind=kind):
                output = self.theme.render_search('product_type:"' + kind + '"', [product(kind, 1)])
                self.assertIn("<h1>" + kind + "</h1>", output)
                self.assertEqual(output.count('<article class="product-card">'), 1)
                self.assertIn("1 parts", output)
                self.assertNotIn("SearchPageInput", output)
                self.assertNotIn("product_type:", output)


class BoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.theme = Theme()

    def first_type(self, value):
        blocks = self.theme.blocks()
        blocks[0]["settings"]["product_type"] = value
        return quoted_type(query(cards(self.theme.render_home(blocks))[0]))

    def test_empty_and_whitespace_types_fall_back(self):
        for value in (None, "", " ", "\t\n", "   "):
            with self.subTest(value=value):
                self.assertEqual(self.first_type(value), TYPES[0])

    def test_type_surrounding_whitespace_is_trimmed(self):
        for value in (" Guitar tuners ", "\tGuitar tuners\n"):
            with self.subTest(value=value):
                self.assertEqual(self.first_type(value), TYPES[0])

    def test_unicode_and_punctuation_round_trip(self):
        for value in ('吉他旋钮', 'Mini "X"', "A\\B", "A&B + C/%", "left:right (wide)", "électric 🎸"):
            with self.subTest(value=value):
                self.assertEqual(self.first_type(value), value)

    def test_illustration_endpoints_and_legacy_defaults(self):
        blocks = self.theme.blocks()
        for block in blocks:
            del block["settings"]["product_type"]
            block["settings"]["title"] = "翻译后的显示名称"
        self.assertEqual([quoted_type(query(link)) for link in cards(self.theme.render_home(blocks))], list(TYPES))

    def test_no_blocks_and_reordered_blocks(self):
        self.assertEqual(cards(self.theme.render_home([])), [])
        self.assertEqual([quoted_type(query(link)) for link in cards(self.theme.render_home(self.theme.blocks()[::-1]))], list(TYPES)[::-1])

    def test_empty_category_stays_empty(self):
        output = self.theme.render_search('product_type:"Knobs"')
        self.assertIn("<h1>Knobs</h1>", output)
        self.assertIn("There are no parts in this category yet.", output)
        self.assertNotIn('<article class="product-card">', output)
        self.assertIn('href="/collections/all"', output)

    def test_malformed_and_compound_queries_stay_search(self):
        for value in ('product_type:"', 'product_type:""', 'product_type:"Knobs',
                      'product_type:"Knobs" OR title:"Other"', 'product_type:"Knobs" tail', 'product_type:Knobs'):
            with self.subTest(value=value):
                output = self.theme.render_search(value)
                self.assertIn("SearchPageInput", output)
                self.assertIn("<h1>Search parts.</h1>", output)

    def test_search_before_submission(self):
        output = self.theme.render_search("", performed=False)
        self.assertIn("SearchPageInput", output)
        self.assertNotIn("results-top", output)

    def test_long_type(self):
        value = "X" * 4096
        self.assertEqual(self.first_type(value), value)


class RegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.theme = Theme()
        cls.base = Theme(BASE)

    def test_ordinary_search_matches_baseline(self):
        for value in ("", "BA-102", 'knobs & "switches"', "吉他"):
            for rows in ([], [product("Knobs", 1)]):
                with self.subTest(value=value, count=len(rows)):
                    self.assertEqual(DOM(self.theme.render_search(value, rows)).events,
                                     DOM(self.base.render_search(value, rows)).events)

    def test_other_home_sections_match_baseline(self):
        without_categories = lambda text: re.sub(r'<section class="section wrap categories".*?</section>', "", text, flags=re.S)
        self.assertEqual(DOM(without_categories(self.theme.render_home())).events,
                         DOM(without_categories(self.base.render_home())).events)

    def test_localized_storefront_routes(self):
        routes = dict(ROUTES, search_url="/zh/search", root_url="/zh/")
        self.assertTrue(all(urlsplit(link).path == "/zh/search" for link in cards(self.theme.render_home(routes=routes))))

    def test_filter_query_survives_pagination(self):
        term = 'product_type:"Guitar tuners"'
        rows = [product(TYPES[0], number) for number in range(25)]
        for page, count in ((1, 24), (2, 1)):
            with self.subTest(page=page):
                output = self.theme.render_search(term, rows, page=page)
                self.assertEqual(output.count('<article class="product-card">'), count)
                pagination = output[output.index('<nav class="ff-pagination"'):]
                for link in re.findall(r'href="([^"]+)"', pagination):
                    self.assertEqual(query(html.unescape(link)), term)


class SecurityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.theme = Theme()

    def test_query_injection_payloads_remain_one_value(self):
        for value in ('Knobs" OR title:"Other', 'Knobs\\" OR product_type:*', '" OR * OR "',
                      'javascript:alert(1)', 'Knobs) OR (vendor:*)', '"\\\\"', '"' * 100):
            with self.subTest(value=value):
                blocks = self.theme.blocks()
                blocks[0]["settings"]["product_type"] = value
                link = cards(self.theme.render_home(blocks))[0]
                self.assertEqual(urlsplit(link).path, "/search")
                self.assertEqual(quoted_type(query(link)), value)

    def test_html_and_attribute_injection_are_escaped(self):
        payload = '\"><img src=x onerror=alert(1)><script>alert(1)</script>'
        blocks = self.theme.blocks()
        blocks[0]["settings"]["title"] = payload
        blocks[0]["settings"]["product_type"] = payload
        home = self.theme.render_home(blocks)
        for markup in (home, self.theme.render_search(query(cards(home)[0])), self.theme.render_search(payload)):
            with self.subTest(markup=markup[:20]):
                for tag, attrs in DOM(markup).tags:
                    self.assertNotEqual(tag, "script")
                    self.assertFalse(any(name.startswith("on") for name in attrs))
                self.assertNotIn('<img src=x', markup)

    def test_fuzz_escaping_and_heading_round_trip(self):
        randomizer = random.Random(20261104)
        alphabet = 'abc XYZ"\\:&<>()/吉他🎸'
        blocks = self.theme.blocks()[:1]
        for index in range(400):
            value = "A" + "".join(randomizer.choices(alphabet, k=randomizer.randint(1, 120))) + "Z"
            with self.subTest(index=index, value=value):
                blocks[0]["settings"]["product_type"] = value
                term = query(cards(self.theme.render_home(blocks))[0])
                self.assertEqual(quoted_type(term), value)
                self.assertIn("<h1>" + html.escape(value, quote=True) + "</h1>", self.theme.render_search(term))


class IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), handler(Theme()))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.origin = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def get(self, path):
        with urlopen(self.origin + path, timeout=10) as response:
            self.assertEqual(response.status, 200)
            return response.read().decode("utf-8")

    def test_click_targets_return_only_the_fixture_category(self):
        for link, kind in zip(cards(self.get("/")), TYPES):
            with self.subTest(kind=kind):
                output = self.get(link)
                names = [html.unescape(name) for name in re.findall(r'<a class="product-name"[^>]*>(.*?)</a>', output)]
                self.assertTrue(names)
                self.assertTrue(all(name.startswith(kind + " ") for name in names), names)
                self.assertNotIn("Uncategorized 33", names)

    def test_pagination_then_product_link(self):
        first = self.get(cards(self.get("/"))[0])
        pagination = first[first.index('<nav class="ff-pagination"'):]
        second_url = html.unescape(re.search(r'href="([^"]+)"[^>]*>2</a>', pagination)[1])
        second = self.get(second_url)
        self.assertEqual(second.count('<article class="product-card">'), 1)
        product_url = re.search(r'<a class="product-name" href="([^"]+)"', second)[1]
        self.assertIn("Guitar tuners", self.get(product_url))

    def test_smoke_home_search_all_and_assets(self):
        for path in ("/", "/search", "/search?type=product&q=Knobs", "/collections/all",
                     "/assets/fretfuel.css", "/assets/fretfuel-theme.css", "/assets/fretfuel-theme.js"):
            with self.subTest(path=path):
                self.assertTrue(self.get(path))


if __name__ == "__main__":
    unittest.main(verbosity=2)
