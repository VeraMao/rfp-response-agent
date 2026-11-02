"""Summary agent loop with a fake model (no API): bad tool arguments, counts by code, the untrusted-input rule,
and the missing-key message."""
import json
import unittest
from types import SimpleNamespace
from unittest import mock

from rfp import assess, crm, extract, llm, summary_agent
from tests.helpers import result

USER = {"id": "dana", "name": "Dana Lee", "role": "sales_rep"}


class FakeResponses:
    """Replays scripted model replies and records what the agent sent back."""

    def __init__(self, replies):
        self.replies, self.inputs = list(replies), []

    def create(self, **kwargs):
        self.inputs.append(list(kwargs["input"]))
        return self.replies.pop(0)


def tool_call(name, arguments, call_id="c1"):
    call = SimpleNamespace(type="function_call", name=name, arguments=arguments, call_id=call_id)
    return SimpleNamespace(output=[call], output_text="")


def final(text):
    return SimpleNamespace(output=[], output_text=text)


class SummaryAgentTests(unittest.TestCase):
    def run_agent(self, replies, rows=()):
        fake = FakeResponses(replies)
        with mock.patch.object(llm, "client", lambda: SimpleNamespace(responses=fake)):
            summary, calls = summary_agent.run("RFP header", "Meridian Health", list(rows), USER, log=lambda *_: None)
        return summary, calls, fake

    def test_malformed_tool_arguments_go_back_to_the_model_as_an_error(self):
        summary, calls, fake = self.run_agent([tool_call("get_customer", "{not json"), final("Done.")])
        self.assertTrue(summary.endswith("Done."))
        outputs = [i for i in fake.inputs[1] if isinstance(i, dict) and i.get("type") == "function_call_output"]
        self.assertEqual(outputs[0]["call_id"], "c1")
        self.assertIn("Bad arguments", json.loads(outputs[0]["output"])["error"])

    def test_step_limit_stops_the_loop(self):
        replies = [tool_call("get_customer", '{"name": "Meridian Health"}', f"c{i}")
                   for i in range(summary_agent.MAX_STEPS)]
        summary, calls, _ = self.run_agent(replies)
        self.assertIn("step limit", summary)
        self.assertEqual(len(calls), summary_agent.MAX_STEPS)


    def test_counts_come_from_the_code_not_the_model(self):
        rows = [{"id": "1", "text": "x", **result(status=s)} for s in ("supported", "conditional", "conditional")]
        summary, _, _ = self.run_agent([final("### Bottom line\nTwo are supported.\n### What it takes to win\n...")],
                                       rows)
        self.assertIn("### Bottom line\n**3 requirements: 1 supported, 2 conditional, 0 not supported, "
                      "0 need review.**", summary)

    def test_price_tool_accepts_only_items_in_the_price_list(self):
        get_pricing = next(t for t in summary_agent.TOOLS if t["name"] == "get_pricing")
        self.assertEqual(get_pricing["parameters"]["properties"]["item"]["enum"], crm.price_items())
        self.assertIn("Enterprise", crm.price_items())


class PromptTests(unittest.TestCase):
    def test_every_prompt_treats_input_as_untrusted(self):
        for prompt in (extract.INSTRUCTIONS, assess.INSTRUCTIONS, summary_agent.INSTRUCTIONS):
            self.assertIn(llm.UNTRUSTED_INPUT_RULE, prompt)


class MissingKeyTest(unittest.TestCase):
    def test_missing_key_gives_one_clear_line(self):
        with mock.patch.dict("os.environ", {}, clear=True), mock.patch.object(llm, "_client", None):
            with self.assertRaises(SystemExit) as err:
                llm.client()
        self.assertIn("OPENAI_API_KEY", str(err.exception.code))


if __name__ == "__main__":
    unittest.main()
