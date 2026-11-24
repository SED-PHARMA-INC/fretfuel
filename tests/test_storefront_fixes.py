import html
import re
import unittest
from urllib.parse import parse_qs, urlencode, urlsplit

from category_harness import ROUTES, TYPES, Theme, product
from test_category_navigation import DOM


def type_query(kind):
    return 'product_type:"' + kind.replace('\\', '\\\\').replace('"', '\\"') + '"'


class CategoryPresentationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.theme = Theme()

    def test_raw_and_shopify_encoded_types_have_category_headings(self):
        kinds = TYPES + ('Mini "X"', 'A&B', 'A &quot; B', "Player's tuner", '吉他旋钮', '<test>')
        for kind in kinds:
            for encoded in (False, True):
                with self.subTest(kind=kind, encoded=encoded):
                    markup = self.theme.render_search(type_query(kind), [product(kind, 1)], html_encoded_terms=encoded)
                    self.assertIn('<h1>' + html.escape(kind, quote=True) + '</h1>', markup)
                    self.assertNotIn('SearchPageInput', markup)
                    self.assertNotIn('product_type:', markup)

    def test_parent_navigation_queries_have_friendly_titles(self):
        homepage = self.theme.page('/')
        nav = re.search(r'<nav class="department-nav".*?</nav>', homepage, re.S)[0]
        for href, label in re.findall(r'<a href="([^"]+)">([^<]+)</a>', nav):
            label = html.unescape(label)
            if label not in ('Tuners', 'Bridges & tailpieces', 'Hardware & small parts'):
                continue
            query = parse_qs(urlsplit(html.unescape(href)).query)['q'][0]
            for encoded in (False, True):
                with self.subTest(label=label, encoded=encoded):
                    markup = self.theme.render_search(query, html_encoded_terms=encoded)
                    self.assertIn('<h1>' + html.escape(label) + '</h1>', markup)
                    self.assertNotIn('SearchPageInput', markup)

    def test_document_title_and_header_do_not_expose_category_query(self):
        markup = self.theme.page('/search?' + urlencode({'type': 'product', 'q': type_query('Pickups')}))
        self.assertIn('<title>Pickups — FretFuel</title>', markup)
        header = re.search(r'<form class="header-search".*?</form>', markup, re.S)[0]
        self.assertIn('value=""', header)
        self.assertNotIn('product_type', header)
        visible = ' '.join(event[1] for event in DOM(markup).events if event[0] == 'text')
        self.assertNotIn('product_type:', visible)

    def test_encoded_invalid_or_unrelated_queries_stay_ordinary_search(self):
        for query in ('product_type:"Knobs" OR title:"Other"', 'product_type:"Knobs" tail',
                      'product_type:""', 'product_type:Knobs', 'BA-102'):
            with self.subTest(query=query):
                markup = self.theme.render_search(query, html_encoded_terms=True)
                self.assertIn('<h1>Search parts.</h1>', markup)
                self.assertIn('SearchPageInput', markup)

    def test_encoded_title_payload_is_escaped(self):
        payload = '"><img src=x onerror=alert(1)>'
        markup = self.theme.render_search(type_query(payload), html_encoded_terms=True)
        self.assertIn('<h1>' + html.escape(payload, quote=True) + '</h1>', markup)
        self.assertNotIn('<img src=x', markup)

    def test_category_pagination_keeps_its_query_and_title(self):
        term = type_query('Guitar tuners')
        first = self.theme.page('/search?' + urlencode({'type': 'product', 'q': term}))
        pagination = re.search(r'<nav class="ff-pagination".*?</nav>', first, re.S)[0]
        second_url = html.unescape(re.search(r'href="([^"]+)"[^>]*>2</a>', pagination)[1])
        self.assertEqual(parse_qs(urlsplit(second_url).query)['q'], [term])
        second = self.theme.page(second_url)
        self.assertIn('<title>Guitar tuners — FretFuel</title>', second)
        self.assertEqual(second.count('<article class="product-card">'), 1)


class CollectionAndGuideTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.theme = Theme()

    def test_empty_series_returns_to_all_products_and_clear_filters_stays_local(self):
        for handle in ('hero', 'stage', 'black', 'black-x'):
            with self.subTest(handle=handle):
                path = '/collections/' + handle
                markup = self.theme.page(path + '?filter.v.availability=1')
                self.assertIn('href="/collections/all">View all parts</a>', markup)
                self.assertIn('href="' + path + '">Clear filters ↗</a>', markup)

    def test_each_home_guide_opens_its_own_existing_topic(self):
        markup = self.theme.render_home()
        for topic in ('replacement-checklist', 'measurement-guide', 'finish-guide'):
            with self.subTest(topic=topic):
                self.assertIn('href="/#' + topic + '"', markup)
                self.assertIn('id="' + topic + '" data-ff-guide', markup)
        self.assertNotIn('href="/#workbench"', markup)
        self.assertEqual(len(re.findall(r'<details\b', markup)), 3)

    def test_custom_topic_links_are_preserved(self):
        settings = {'guide_url': '/pages/custom-checklist',
                    'measurement_guide_url': '/pages/custom-measurements#dimensions',
                    'finish_guide_url': 'https://example.com/finishes'}
        markup = self.theme.render_home(overrides=settings)
        for url in settings.values():
            self.assertIn('href="' + url + '"', markup)

    def test_legacy_default_guide_link_uses_the_localized_topic(self):
        routes = dict(ROUTES, root_url='/zh/')
        markup = self.theme.render_home(routes=routes, overrides={'guide_url': '/#workbench'})
        for topic in ('replacement-checklist', 'measurement-guide', 'finish-guide'):
            self.assertIn('href="/zh/#' + topic + '"', markup)
        self.assertNotIn('href="/#workbench"', markup)

    def test_standalone_guide_reuses_all_topics_and_shows_checklist_without_javascript(self):
        markup = self.theme.page('/pages/parts-guide')
        self.assertIn('id="replacement-checklist" data-ff-guide open', markup)
        for heading in ('Replacement checklist', 'Measuring replacement parts', 'Comparing hardware finishes'):
            self.assertIn('<summary>' + heading + '</summary>', markup)
        self.assertIn('String spacing, mounting post spacing and screw hole spacing', markup)


if __name__ == '__main__':
    unittest.main()
