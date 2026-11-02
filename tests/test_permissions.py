import unittest

from rfp import knowledge, permissions
from rfp.retrieve import Index
from tests.helpers import fake_embed

RESTRICTED_DOCS = {"legal-negotiation.md", "pricing-policy.md"}


class PermissionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.chunks = knowledge.load_chunks()
        cls.index = Index(cls.chunks, embed_fn=fake_embed)

    def docs_seen(self, role, query):
        return {c["doc"] for _, c in self.index.search(query, role, k=len(self.chunks))}

    def test_sales_rep_never_retrieves_restricted_text_even_when_asking_for_it(self):
        for query in ["discount approval sales managers 25%", "liability cap exceptions 2x annual fees"]:
            self.assertFalse(self.docs_seen("sales_rep", query) & RESTRICTED_DOCS)

    def test_manager_sees_discount_policy_and_negotiation_positions(self):
        self.assertTrue(RESTRICTED_DOCS <= self.docs_seen("sales_manager", "discount liability"))

    def test_legal_sees_negotiation_but_not_discount_policy(self):
        seen = self.docs_seen("legal", "discount liability")
        self.assertIn("legal-negotiation.md", seen)
        self.assertNotIn("pricing-policy.md", seen)

    def test_hidden_count(self):
        hidden = self.index.hidden_count("sales_rep")
        expected = sum(c["doc"] in RESTRICTED_DOCS for c in self.chunks)
        self.assertEqual(hidden, expected)
        self.assertGreater(hidden, 0)

    def test_every_user_has_a_known_role(self):
        for uid, u in permissions.load_users().items():
            self.assertIn(u["role"], {"sales_rep", "sales_manager", "legal"}, uid)


if __name__ == "__main__":
    unittest.main()
