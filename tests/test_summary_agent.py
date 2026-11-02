"""Summary agent loop with a fake model (no API): bad tool arguments, and the untrusted-input rule."""
import json
import unittest
from types import SimpleNamespace
from unittest import mock

from rfp import assess, extract, llm, summary_agent

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
    def run_agent(self, replies):
        fake = FakeResponses(replies)
        with mock.patch.object(llm, "client", lambda: SimpleNamespace(responses=fake)):
            summary, calls = summary_agent.run("RFP header", "Meridian Health", [], USER, log=lambda *_: None)
        return summary, calls, fake

    def test_malformed_tool_arguments_go_back_to_the_model_as_an_error(self):
        summary, calls, fake = self.run_agent([tool_call("get_customer", "{not json"), final("Done.")])
        self.assertEqual(summary, "Done.")
        outputs = [i for i in fake.inputs[1] if isinstance(i, dict) and i.get("type") == "function_call_output"]
        self.assertEqual(outputs[0]["call_id"], "c1")
        self.assertIn("Bad arguments", json.loads(outputs[0]["output"])["error"])

    def test_step_limit_stops_the_loop(self):
        replies = [tool_call("get_customer", '{"name": "Meridian Health"}', f"c{i}")
                   for i in range(summary_agent.MAX_STEPS)]
        summary, calls, _ = self.run_agent(replies)
        self.assertIn("step limit", summary)
        self.assertEqual(len(calls), summary_agent.MAX_STEPS)


class PromptTests(unittest.TestCase):
    def test_every_prompt_treats_input_as_untrusted(self):
        for prompt in (extract.INSTRUCTIONS, assess.INSTRUCTIONS, summary_agent.INSTRUCTIONS):
            self.assertIn(llm.UNTRUSTED_INPUT_RULE, prompt)


if __name__ == "__main__":
    unittest.main()
