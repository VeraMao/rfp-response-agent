"""Step 6: Deal Summary Agent.

Reads the assessed requirements and decides what else to look up (CRM, pricing) before writing a
summary for the sales rep. The per-requirement steps are fixed, so they are a pipeline; what to look
up next depends on the results, so this part is an agent. Its tools are read-only.
"""
import json

from rfp import config, crm, llm

MAX_STEPS = 5

TOOLS = [
    {"type": "function", "name": "get_customer",
     "description": "Look up a customer in the CRM: relationship, current plan, users, account owner, "
                    "renewal date and notes.",
     "parameters": {"type": "object", "properties": {"name": {"type": "string", "description": "Exact account name"}},
                    "required": ["name"]}},
    {"type": "function", "name": "get_pricing",
     "description": "Get list pricing for a plan or service (Standard, Enterprise, Fast-track), plus the "
                    "maximum discount the current user may offer.",
     "parameters": {"type": "object", "properties": {"item": {"type": "string"}}, "required": ["item"]}},
]

INSTRUCTIONS = """You write a short deal summary for a sales rep who must decide how to respond to an RFP.
You get the RFP header, the customer name and our assessment of each requirement. Use the tools when the
answer depends on the customer's current situation or on price; don't call tools you don't need.

Write exactly three sections, in markdown:
### Bottom line
How many requirements are supported, conditional, not supported, or still unknown, and whether we can respond.
### What it takes to win
Plan changes, costs and customer obligations needed to meet the conditional requirements.
### Customer context and open risks
The customer's current situation from the CRM, every not-supported or unknown item, and every source
conflict, each with who must confirm it.

Rules:
- Use only facts from the assessment and tool results. Never invent numbers.
- Do not compute a total price unless every input (such as the number of users in scope) is known;
  if one is missing, say what is missing.
- Mark each fact's source in brackets: [Assessment 3.2], [CRM], [Pricing].
- Internal note for our team, not text for the customer. Under 250 words."""


def run(rfp_header, customer, rows, user, log=print):
    registry = {"get_customer": lambda name: crm.get_customer(name),
                "get_pricing": lambda item: crm.get_pricing(item, user["role"])}     # role is fixed by code
    assessment = "\n".join(
        f"- {r['id']} {r['status']}: {r['text']} | conditions: {r['conditions'] or 'none'} | "
        f"owner: {r['owner'] or 'none'}{' | CONFLICT: ' + r['conflict'] if r.get('conflict') else ''}"
        for r in rows)
    items = [{"role": "user", "content": f"RFP header:\n{rfp_header}\n\nCustomer: {customer}\n\n"
                                         f"Assessment:\n{assessment}"}]
    calls_made = []
    for step in range(1, MAX_STEPS + 1):
        resp = llm.client().responses.create(model=config.MODEL, instructions=INSTRUCTIONS, input=items,
                                             tools=TOOLS, temperature=0)
        calls = [o for o in resp.output if o.type == "function_call"]
        if not calls:
            return resp.output_text, calls_made
        items += resp.output
        for c in calls:
            args = json.loads(c.arguments)
            func = registry.get(c.name)
            try:
                result = func(**args) if func else {"error": f"Unknown tool: {c.name}"}
            except TypeError as exc:                                     # wrong arguments -> tell the model
                result = {"error": f"Bad arguments for {c.name}: {exc}"}
            log(f"   [agent step {step}] {c.name}({args}) -> {result}")
            calls_made.append(f"{c.name}({', '.join(str(v) for v in args.values())})")
            items.append({"type": "function_call_output", "call_id": c.call_id, "output": json.dumps(result)})
    return "Summary unavailable: the agent reached its step limit. Review the requirements below.", calls_made
