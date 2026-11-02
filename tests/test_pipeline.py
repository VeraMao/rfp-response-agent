"""Wiring test for steps 2-5 with a fake model (no API): retrieval, library reuse, checks, draft."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from rfp import config, draft, knowledge, pipeline
from rfp.retrieve import Index
from tests.helpers import fake_embed

USER = {"id": "dana", "name": "Dana Lee", "role": "sales_rep"}


def fake_assess(req, evidence, hint=None, today=None):
    """Pretend model: always 'supported', citing the top passage; remembers the hint it was given."""
    fake_assess.hints.append(hint)
    return {"status": "supported", "answer": "We do.", "conditions": None,
            "citations": [evidence[0][1]["id"]], "conflict": None, "owner": None}


class PipelineTests(unittest.TestCase):
    def setUp(self):
        fake_assess.hints = []
        self.tmp = tempfile.TemporaryDirectory()
        self.old_data, config.DATA = config.DATA, Path(self.tmp.name)
        self.index = Index(knowledge.load_chunks(), embed_fn=fake_embed)

    def tearDown(self):
        config.DATA = self.old_data
        self.tmp.cleanup()

    def run_one(self, text):
        with mock.patch("rfp.assess.assess", fake_assess):
            return pipeline.assess_requirements([{"id": "1", "text": text}], self.index, USER, log=lambda *_: None)

    def write_library(self, updated_cid, approved_on):
        entry = {"id": "L-001", "requirement": "Single sign-on with Okta", "status": "supported", "answer": "We do.",
                 "conditions": None, "citations": [updated_cid], "approved_by": "Dana", "approved_on": approved_on}
        (config.DATA / "answer_library.json").write_text(json.dumps([entry]))

    def test_reuses_an_approved_answer_whose_sources_are_unchanged(self):
        self.write_library("product.md#Authentication", "2026-10-30")
        row = self.run_one("Single sign-on with Okta")[0]
        self.assertEqual(row["reused_from"], "L-001")
        self.assertIn("Previously approved answer L-001", fake_assess.hints[0])

    def test_does_not_reuse_when_a_source_changed_after_approval(self):
        self.write_library("product.md#Authentication", "2026-01-01")      # product.md updated 2026-09-15
        row = self.run_one("Single sign-on with Okta")[0]
        self.assertIsNone(row["reused_from"])
        self.assertIn("approved before", row["library_note"])
        self.assertIsNone(fake_assess.hints[0])

    def test_rows_render_in_the_draft(self):
        rows = self.run_one("Single sign-on with Okta")
        md = draft.build("Meridian Health", rows, USER, hidden=3)
        self.assertIn("✅ Supported", md)
        self.assertIn("3 document sections were hidden", md)


if __name__ == "__main__":
    unittest.main()
