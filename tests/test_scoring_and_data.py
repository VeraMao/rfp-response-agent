import json
import tempfile
import unittest
from pathlib import Path

from rfp import config, crm, knowledge, scoring


class ScoringTests(unittest.TestCase):
    exp = {"status": ["conditional"], "conditions_must_mention": ["enterprise"],
           "answer_must_not_mention": ["99.95"], "conflict": True, "expected_evidence": ["product.md"]}

    def test_pass(self):
        r = {"status": "conditional", "answer": "We guarantee 99.9% on our Enterprise plan.",
             "conditions": "Enterprise plan only.", "citations": ["product.md#SLA"], "conflict": "old deck says 99.95",
             "owner": "Product"}
        self.assertEqual(scoring.score_requirement(self.exp, r), [])

    def test_internal_note_in_answer_fails(self):
        r = {"status": "conditional", "answer": "Please verify the report.", "conditions": "Enterprise",
             "citations": ["x"], "conflict": "c", "owner": "Product"}
        self.assertIn("answer contains 'verify'", scoring.score_requirement(self.exp, r))

    def test_internal_words_match_whole_words_only(self):
        self.assertFalse(scoring.mentions("we do not currently offer pci dss.", "not current"))
        self.assertTrue(scoring.mentions("the report is not current as of today.", "not current"))
        self.assertTrue(scoring.mentions("based on the passages, we", "passage"))

    def test_recall(self):
        self.assertTrue(scoring.recall_hit(self.exp, ["product.md#Plans", "x.md#Y"]))
        self.assertFalse(scoring.recall_hit(self.exp, ["x.md#Y"]))

    def test_invented_price(self):
        allowed = {55.0, 15000.0}
        fails = scoring.score_summary("### Bottom line ### What it takes to win ### Customer context "
                                      "$55 per user, $15,000 fee, total $26,400", ["get_customer(X)"], allowed)
        self.assertEqual(fails, ["invented price $26,400"])


class CrmTests(unittest.TestCase):
    def test_each_role_sees_only_its_own_discount_limit(self):
        self.assertEqual(crm.get_pricing("Enterprise", "sales_rep")["your_max_discount_pct"], 10)
        self.assertEqual(crm.get_pricing("Enterprise", "sales_manager")["your_max_discount_pct"], 25)
        self.assertNotIn("your_max_discount_pct", crm.get_pricing("Enterprise", "legal"))

    def test_identical_crm_write_is_not_repeated(self):
        with tempfile.TemporaryDirectory() as tmp:
            old, config.OUTPUTS = config.OUTPUTS, Path(tmp)
            try:
                update = {"account": "Meridian Health", "activity": "RFP draft prepared", "date": "2026-11-01",
                          "summary": "1 supported", "open_items": ["3.2 -> Product"]}
                self.assertTrue(crm.write_update(update, "Dana Lee")[1])
                self.assertFalse(crm.write_update(dict(update), "Marco Ruiz")[1])     # double click / re-run
                self.assertTrue(crm.write_update({**update, "summary": "2 supported"}, "Dana Lee")[1])
                self.assertEqual(len(json.loads((Path(tmp) / "crm_updates.json").read_text())), 2)
            finally:
                config.OUTPUTS = old

    def test_unknown_items_are_errors_not_exceptions(self):
        self.assertIn("error", crm.get_pricing("Platinum", "sales_rep"))
        self.assertIn("error", crm.get_customer("Nobody Inc"))


class DataTests(unittest.TestCase):
    """The test data itself must be consistent, or eval scores mean nothing."""

    def test_every_document_has_metadata(self):
        for c in knowledge.load_chunks():
            self.assertRegex(c["updated"], r"^\d{4}-\d{2}-\d{2}$", c["id"])
            self.assertTrue(c["owner"], c["id"])
            self.assertIn(c["visibility"], {"public", "internal", "restricted"}, c["id"])
            if c["visibility"] == "restricted":
                self.assertTrue(c["allowed_roles"], c["id"])

    def test_plan_names_come_from_documents(self):
        self.assertEqual(knowledge.plan_names(knowledge.load_chunks()), ["Enterprise", "Standard"])

    def test_expected_files_match_rfps_and_documents(self):
        docs = {p.name for p in config.KNOWLEDGE.glob("*.md")}
        for f in config.EXPECTED.glob("*.json"):
            exp = json.loads(f.read_text())
            rfp_text = (config.RFPS / f"{f.stem}.txt").read_text()
            for rid, e in exp["requirements"].items():
                self.assertIn(rid, rfp_text, f"{f.stem} {rid}")
                for d in e["expected_evidence"]:
                    self.assertIn(d, docs, f"{f.stem} {rid}")
                for s in e["status"]:
                    self.assertIn(s, config.STATUSES)
            self.assertIn(exp["customer"], json.loads((config.DATA / "crm.json").read_text()))


if __name__ == "__main__":
    unittest.main()
