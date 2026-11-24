import html
from pathlib import Path
import re
import unittest

from category_harness import Theme
from test_category_navigation import DOM


def workbench(markup):
    return re.search(r'<section class="section workbench-section".*?</section>', markup, re.S)[0]


class OriginalGuideTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.theme = Theme()

    def test_guide_section_matches_original_html_structure_and_text(self):
        original = Path(__file__).with_name('fixtures').joinpath('original-guide-section.html').read_text(encoding='utf-8')
        def events(markup):
            result = []
            for event in DOM(markup).events:
                if event[0] in ('button', 'svg'):
                    event = (event[0], tuple((key, value) for key, value in event[1]
                                            if key not in ('type', 'aria-hidden')))
                result.append(event)
            return result
        self.assertEqual(events(workbench(self.theme.render_home())), events(original))

    def test_three_distinct_guides_have_closed_labelled_dialogs(self):
        page = self.theme.page('/')
        for topic, title, phrase in (
                ('basics', 'Replacement part checklist.', 'Begin with your existing part.'),
                ('measure', 'Measuring replacement parts.', 'A number is only useful when you know where it starts and ends.'),
                ('finish', 'Comparing hardware finishes.', 'Colour and surface are separate details')):
            with self.subTest(topic=topic):
                dialog = re.search(r'<dialog id="ff-guide-' + topic + r'".*?</dialog>', page, re.S)[0]
                attrs = DOM(dialog).tags[0][1]
                self.assertNotIn('open', attrs)
                self.assertEqual(attrs['aria-labelledby'], 'ff-guide-' + topic + '-title')
                self.assertIn(title, dialog)
                self.assertIn(phrase, dialog)
                self.assertIn('data-guide-close', dialog)
        self.assertNotIn('data-ff-guide>', page)

    def test_finder_category_browse_links_match_department_navigation(self):
        page = self.theme.page('/')
        navigation = re.search(r'<nav class="department-nav".*?</nav>', page, re.S)[0]
        destinations = [html.unescape(url) for url in re.findall(r'<a href="([^"]+)"', navigation)
                        if '/search?' in url]
        self.assertEqual(len(destinations), 6)
        for category, destination in zip(('tuners', 'bridges', 'pickups', 'electronics', 'pickguards', 'small'), destinations):
            with self.subTest(category=category):
                self.assertIn('data-finder-category="' + category + '"', page)
                panel = re.search(r'<div data-ff-finder-panel="' + category + r'".*?<div class="finder-bottom">.*?</div>', page, re.S)[0]
                target = re.search(r'<a class="button dark" href="([^"]+)"', panel)[1]
                self.assertEqual(html.unescape(target), destination)
                self.assertEqual(panel.count('class="finder-step"'), 3)

    def test_configured_guide_url_overrides_dialog_buttons(self):
        url = '/pages/custom-guide?part=bridge&finish=gold'
        markup = workbench(self.theme.render_home(overrides={'guide_url': url}))
        self.assertEqual(markup.count('href="' + html.escape(url, quote=True) + '"'), 3)
        self.assertNotIn('<button', markup)

    def test_legacy_workbench_setting_restores_original_dialogs(self):
        for setting in ('', '/#workbench', '#workbench'):
            with self.subTest(setting=setting):
                markup = self.theme.render_home(overrides={'guide_url': setting})
                for topic in ('basics', 'measure', 'finish'):
                    self.assertIn('data-guide="' + topic + '"', markup)
                self.assertIn('data-finder', markup)


if __name__ == '__main__':
    unittest.main()
