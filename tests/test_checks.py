import unittest
from datetime import date

from rfp.checks import check
from tests.helpers import chunk, result

TODAY = date(2026, 10, 31)
PLANS = ["Enterprise", "Standard"]


class CheckTests(unittest.TestCase):
    def ev(self, *chunks):
        return [(0.9, c) for c in chunks]

    def test_invented_citation_is_dropped_and_claim_becomes_needs_review(self):
        r = check(result(citations=["made-up.md#X"]), self.ev(chunk("a.md#X", "We support SSO.")), PLANS, TODAY)
        self.assertEqual(r["citations"], [])
        self.assertEqual(r["status"], "not_found")
        self.assertTrue(r["owner"])

    def test_a_no_also_needs_evidence(self):
        r = check(result(status="not_supported", citations=[]), self.ev(chunk("a.md#X", "x")), PLANS, TODAY)
        self.assertEqual(r["status"], "not_found")

    def test_stale_source_downgrades_supported(self):
        old = chunk("old.md#X", "We guarantee 99.95% uptime.", updated="2024-03-01")
        r = check(result(citations=["old.md#X"]), self.ev(old), PLANS, TODAY)
        self.assertEqual(r["status"], "conditional")
        self.assertIn("2024-03-01", r["conditions"])

    def test_unknown_date_counts_as_stale(self):
        r = check(result(citations=["a.md#X"]), self.ev(chunk("a.md#X", "x", updated="unknown")), PLANS, TODAY)
        self.assertEqual(r["status"], "conditional")

    def test_conflict_is_never_supported(self):
        r = check(result(conflict="A says 99.9, B says 99.95"), self.ev(chunk("a.md#X", "x")), PLANS, TODAY)
        self.assertEqual(r["status"], "conditional")

    def test_plan_named_in_evidence_is_added_to_conditions(self):
        ev = self.ev(chunk("a.md#X", "Enterprise customers can choose Fast-track."))
        r = check(result(status="conditional", conditions="Assign a project lead."), ev, PLANS, TODAY)
        self.assertIn("Enterprise", r["conditions"])

    def test_plan_rule_leaves_conditions_alone_when_a_plan_is_already_named(self):
        ev = self.ev(chunk("a.md#X", "Standard 99.5%. Enterprise 99.9%."))
        r = check(result(status="conditional", conditions="Only on the Enterprise plan."), ev, PLANS, TODAY)
        self.assertEqual(r["conditions"], "Only on the Enterprise plan.")

    def test_supported_with_fresh_evidence_is_untouched(self):
        r = check(result(), self.ev(chunk("a.md#X", "We support SSO.")), PLANS, TODAY)
        self.assertEqual(r["status"], "supported")
        self.assertIsNone(r["owner"])

    def test_every_flag_gets_an_owner(self):
        r = check(result(status="not_supported"), self.ev(chunk("a.md#X", "We don't.")), PLANS, TODAY)
        self.assertTrue(r["owner"])


if __name__ == "__main__":
    unittest.main()
