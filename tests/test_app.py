"""Review UI run headless with Streamlit's AppTest and a fake pipeline (no API): editing resets an approval."""
import unittest
from pathlib import Path
from unittest import mock

from streamlit.testing.v1 import AppTest

from rfp import knowledge

APP = str(Path(__file__).resolve().parent.parent / "app.py")


def row(rid, cid):
    return {"id": rid, "text": f"Requirement {rid}?", "status": "supported", "answer": f"Yes {rid}.",
            "conditions": None, "citations": [cid], "searched": [cid], "conflict": None, "owner": None}


class ReviewUITests(unittest.TestCase):
    def setUp(self):
        cid = knowledge.load_chunks()[0]["id"]
        fake = {"rfp": "meridian", "user": {"id": "dana", "name": "Dana Lee", "role": "sales_rep"},
                "customer": "Acme", "rows": [row("1", cid), row("2", cid)], "summary": None, "calls": [], "hidden": 0}
        patches = [mock.patch("rfp.pipeline.run", return_value=fake), mock.patch("rfp.pipeline.build_index"),
                   mock.patch("rfp.llm.has_key", return_value=True),
                   mock.patch("rfp.library.add", return_value={"id": "L1"}),   # don't touch the real library
                   mock.patch("rfp.library.remove", return_value=True), mock.patch("rfp.audit.log")]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.at = AppTest.from_file(APP, default_timeout=30)
        self.at.run()
        self.at.selectbox[0].set_value("meridian").run()
        self.at.button[0].click().run()

    def test_editing_an_approved_answer_resets_it_and_blocks_export(self):
        at = self.at
        for r in at.radio:
            r.set_value("Approve")
        at.run()
        self.assertEqual(len(at.get("download_button")), 1)
        at.text_area[0].set_value("Yes 1, edited.").run()
        self.assertEqual(at.radio[0].value, "Pending")
        self.assertEqual(len(at.get("download_button")), 0)
        at.radio[0].set_value("Approve").run()                     # approving the new text unlocks export again
        self.assertEqual(len(at.get("download_button")), 1)


if __name__ == "__main__":
    unittest.main()
