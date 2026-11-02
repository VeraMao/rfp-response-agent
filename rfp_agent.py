"""RFP Response Agent: command line.

    .venv/bin/python rfp_agent.py                         # meridian RFP, as Dana (sales rep)
    .venv/bin/python rfp_agent.py --rfp harbor_bank --user marco
    .venv/bin/python rfp_agent.py --review                # approve answers one by one -> answer library

Output: outputs/draft_<rfp>.md. Nothing is sent; the CRM is only written after you type 'yes'.
"""
import argparse
import json

from rfp import audit, config, crm, draft, library, pipeline


def ask(question):
    try:
        return input(question).strip().lower()
    except EOFError:                       # no keyboard (e.g. piped): treat as "no"
        return ""


def review(rows, user):
    """Human review in the terminal: approved answers go to the answer library."""
    for r in rows:
        print(f"\n{r['id']} [{r['status']}] {r['text']}\n  Answer: {r['answer']}\n  Conditions: {r['conditions']}")
        if ask("  Approve this answer? (yes/no): ") == "yes":
            entry = library.add(r, user["name"])
            audit.log("approve_answer", user["name"], requirement=r["id"], library_id=entry["id"])
            print(f"  Saved to the answer library as {entry['id']}.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rfp", default="meridian", help="file name in data/rfps without .txt")
    parser.add_argument("--user", default="dana", help="user id from data/users.json")
    parser.add_argument("--review", action="store_true", help="approve answers into the answer library")
    parser.add_argument("--no-summary", action="store_true")
    args = parser.parse_args()

    result = pipeline.run(args.rfp, args.user, with_summary=not args.no_summary)
    user, rows = result["user"], result["rows"]
    out = config.OUTPUTS / f"draft_{args.rfp}.md"
    config.OUTPUTS.mkdir(exist_ok=True)
    out.write_text(draft.build(result["customer"], rows, user, result["summary"], result["calls"], result["hidden"]))
    print(f"\nDraft written to {out}")

    if args.review:
        review(rows, user)

    # Step 7: a WRITE. Code proposes it, a human approves it, then code writes it.
    update = crm.propose_update(result["customer"], rows)
    print("\nProposed CRM update (WRITE):\n" + json.dumps(update, indent=2))
    if ask("Write this to the CRM? Type 'yes' to approve: ") == "yes":
        print(f"Written to {crm.write_update(update, user['name'])} (simulated CRM).")
    else:
        print("Not written. Nothing was changed in the CRM.")


if __name__ == "__main__":
    main()
