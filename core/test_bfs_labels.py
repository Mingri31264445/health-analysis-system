import json
from pathlib import Path

from django.test import SimpleTestCase

from .services.bfs.labels import TEMPLATE_TITLES, template_title

CONFIG = Path(__file__).parent / "services" / "bfs" / "data" / "templates_config.json"


class BfsLabelTests(SimpleTestCase):
    def test_every_configured_template_has_a_title(self):
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(set(config), set(TEMPLATE_TITLES))
        for key in config:
            self.assertTrue(template_title(key))

    def test_unknown_template_has_no_title(self):
        self.assertEqual(template_title(""), "")
        self.assertEqual(template_title("bfs99"), "")
