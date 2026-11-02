"""Step 3: judge one requirement against its evidence (structured outputs)."""
from datetime import date

from rfp import config, llm

SCHEMA = {
    "type": "object",
    "properties": {
        "status": {"type": "string", "enum": config.STATUSES},
        "answer": {"type": "string", "description": "Draft answer to the customer, using only the passages."},
        "conditions": {"type": ["string", "null"], "description": "Conditions, caveats and things to verify."},
        "citations": {"type": "array", "items": {"type": "string"}, "description": "Passage ids used."},
        "conflict": {"type": ["string", "null"],
                     "description": "If passages disagree: what each says and which is newer. null if none."},
        "owner": {"type": ["string", "null"], "enum": config.OWNERS + [None],
                  "description": "Team that should confirm this before sending. null only if fully supported."},
    },
    "required": ["status", "answer", "conditions", "citations", "conflict", "owner"],
    "additionalProperties": False,
}

INSTRUCTIONS = (
    "You check whether our company meets one RFP requirement, using ONLY the passages given. "
    "supported = a passage clearly says we meet it fully, today. "
    "conditional = we meet it only with conditions (a specific plan, a customer obligation, a time limit, "
    "an NDA, a partial match), or the evidence may be out of date compared with today's date. "
    "not_supported = a passage clearly says we do NOT meet it, or it is only planned for the future. "
    "not_found = no passage addresses the requirement at all. "
    "Planned or roadmap items are not current capabilities: never present them as available. "
    "Numbers: if what we offer meets or beats the number asked for (e.g. data deleted within 30 days when "
    "60 is required), the requirement is met. "
    "An audit report or certification covering a past period is still our latest one: if its period has ended, "
    "use conditional and state the period in 'conditions'; never call it not_supported for that reason alone. "
    "Never guess or use outside knowledge. "
    "'answer': write it as our reply to the customer, in our voice ('We ...'). It states only what we can "
    "commit to, with its condition (e.g. 'We guarantee 99.9% uptime on our Enterprise plan.'). Do not include "
    "internal reasoning, comparisons with plans that don't qualify, future plans or dates of plans, or words "
    "like 'the passages'. If status is not_supported, say plainly and politely that we do not currently offer "
    "it. If status is not_found, answer with: 'We will confirm this requirement and follow up.' "
    "Doubts, caveats and things to verify belong in 'conditions', never in 'answer'. "
    "'conditions': list EVERY condition, including which plan is required, customer obligations and dates "
    "to verify. If a passage limits something to a plan or customer type (e.g. 'Enterprise customers'), "
    "that is a condition. For not_supported, put any future plan here for the sales rep. "
    "Each passage shows when it was last updated. If passages disagree, base the answer on the most "
    "recently updated one, describe the disagreement in 'conflict', and never use supported. "
    "Otherwise 'conflict' is null. "
    "'owner': the team that should confirm the answer before it is sent (null only if fully supported). "
    "If a previously approved answer is given, reuse its wording only where today's passages still support it. "
    "Cite the passage ids you used (not the approved-answer id)."
)


def format_passages(evidence):
    return "\n\n".join(f"[{c['id']}] (last updated {c['updated']}, owner {c['owner']})\n{c['text']}"
                       for _, c in evidence)


def assess(req, evidence, library_hint=None, today=None):
    text = (f"Today's date: {(today or date.today()).isoformat()}\n\n"
            f"Requirement {req['id']}: {req['text']}\n\nPassages:\n{format_passages(evidence)}")
    if library_hint:
        text += f"\n\n{library_hint}"
    return llm.ask_json(INSTRUCTIONS, text, SCHEMA, name="assessment")
