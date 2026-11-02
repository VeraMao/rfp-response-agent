import tempfile
import unittest
from datetime import date
from pathlib import Path

from rfp import config, library
from tests.helpers import chunk, fake_embed


class LibraryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_data, config.DATA = config.DATA, Path(self.tmp.name)

    def tearDown(self):
        config.DATA = self.old_data
        self.tmp.cleanup()

    def entry(self, approved_on="2026-10-01", citations=("a.md#X",)):
        return {"id": "L-001", "requirement": "Support SSO with Okta", "status": "supported", "answer": "We do.",
                "conditions": None, "citations": list(citations), "approved_by": "Dana", "approved_on": approved_on}

    ROW = {"text": "Support SSO with Okta", "status": "supported", "answer": "We do.", "conditions": None,
           "citations": ["a.md#X"]}

    def test_add_and_load(self):
        e = library.add(self.ROW, "Dana Lee", "meridian:3.1", today=date(2026, 10, 31))
        self.assertEqual(e["id"], "L-001")
        self.assertEqual(library.load()[0]["approved_on"], "2026-10-31")

    def test_approving_the_same_requirement_again_replaces_it(self):
        library.add(self.ROW, "Dana Lee", "meridian:3.1")
        library.add({**self.ROW, "answer": "We do, edited."}, "Dana Lee", "meridian:3.1")
        entries = library.load()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["answer"], "We do, edited.")
        self.assertEqual(entries[0]["id"], "L-002")              # a withdrawn id is never reused

    def test_withdrawn_approval_is_removed(self):
        library.add(self.ROW, "Dana Lee", "meridian:3.1")
        library.add(self.ROW, "Dana Lee", "harbor_bank:R-01")
        self.assertTrue(library.remove("meridian:3.1"))
        self.assertEqual([e["source"] for e in library.load()], ["harbor_bank:R-01"])
        self.assertFalse(library.remove("meridian:3.1"))

    def test_usable_when_sources_unchanged(self):
        ok, _ = library.usable(self.entry(), {"a.md#X": chunk("a.md#X", "x", updated="2026-09-01")}, "sales_rep")
        self.assertTrue(ok)

    def test_not_usable_when_source_updated_after_approval(self):
        ok, note = library.usable(self.entry(), {"a.md#X": chunk("a.md#X", "x", updated="2026-10-15")}, "sales_rep")
        self.assertFalse(ok)
        self.assertIn("updated", note)

    def test_not_usable_when_source_removed(self):
        ok, _ = library.usable(self.entry(), {}, "sales_rep")
        self.assertFalse(ok)

    def test_not_usable_when_source_hidden_from_role(self):
        hidden = chunk("a.md#X", "x", visibility="restricted", roles=["legal"])
        ok, note = library.usable(self.entry(), {"a.md#X": hidden}, "sales_rep")
        self.assertFalse(ok)
        self.assertIn("can't see", note)

    def test_find_needs_a_close_match(self):
        entries = [self.entry()]
        self.assertIsNotNone(library.find("Support SSO with Okta", entries, fake_embed))
        self.assertIsNone(library.find("Monthly billing is required", entries, fake_embed))


if __name__ == "__main__":
    unittest.main()
