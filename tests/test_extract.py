"""Extraction completeness check (no API): requirements the model skipped are found in the RFP text."""
import json
import unittest

from rfp import checks, config, extract
from tests.helpers import result


def expected_requirements(name):
    """What a perfect extraction returns for one of our RFPs (ids from data/expected)."""
    ids = json.loads((config.EXPECTED / f"{name}.json").read_text())["requirements"]
    return [{"id": rid, "text": "..."} for rid in ids], (config.RFPS / f"{name}.txt").read_text()


class FindMissingTests(unittest.TestCase):
    def test_id_shape_learns_the_numbering_style(self):
        self.assertRegex("R-13", extract.id_shape("R-04"))
        self.assertRegex("4.12", extract.id_shape("3.1"))
        self.assertNotRegex("1.", extract.id_shape("3.1"))           # a section heading is not a requirement

    def test_complete_extraction_has_nothing_missing(self):
        for name in ("meridian", "harbor_bank", "lumen_retail"):
            reqs, text = expected_requirements(name)
            self.assertEqual(extract.find_missing(text, reqs), [], name)

    def test_a_skipped_requirement_is_found_with_its_text(self):
        for name in ("meridian", "harbor_bank", "lumen_retail"):
            reqs, text = expected_requirements(name)
            dropped = reqs.pop(len(reqs) // 2)
            missing = extract.find_missing(text, reqs)
            self.assertEqual([m["id"] for m in missing], [dropped["id"]], name)
            self.assertIn(missing[0]["text"], text)

    def test_nothing_extracted_means_nothing_to_compare(self):
        self.assertEqual(extract.find_missing("3.1 Anything.", []), [])


class FlagRecoveredTests(unittest.TestCase):
    def test_recovered_requirement_is_never_plain_supported(self):
        r = checks.flag_recovered(result(status="supported"))
        self.assertEqual(r["status"], "conditional")
        self.assertIn("Missed by the extraction step", r["conditions"])
        self.assertTrue(r["owner"])

    def test_other_statuses_keep_their_status(self):
        self.assertEqual(checks.flag_recovered(result(status="not_supported"))["status"], "not_supported")


if __name__ == "__main__":
    unittest.main()
