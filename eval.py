"""Evaluation over every RFP in data/rfps against data/expected/<rfp>.json.

    .venv/bin/python eval.py                          # all RFPs, 1 run, as Dana (sales rep)
    .venv/bin/python eval.py --rfp meridian --runs 3  # one RFP, 3 runs (is it stable?)
    .venv/bin/python eval.py --mode hybrid            # compare retrieval modes
    .venv/bin/python eval.py --no-summary             # skip the agent (cheaper)

Two separate scores, so a failure can be blamed on the right step:
  retrieval recall  - did we retrieve the documents a correct answer needs?
  answer checks     - status, conditions, no internal notes in the answer, conflicts, citations, owner
"""
import argparse
import json
from datetime import datetime

from rfp import config, crm, permissions, pipeline, scoring, summary_agent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rfp", default="all")
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--user", default="dana")
    parser.add_argument("--mode", choices=["embed", "hybrid"], default=config.RETRIEVAL)
    parser.add_argument("--no-summary", action="store_true")
    args = parser.parse_args()
    config.RETRIEVAL = args.mode

    names = sorted(p.stem for p in config.EXPECTED.glob("*.json")) if args.rfp == "all" else [args.rfp]
    user = permissions.get_user(args.user)
    index = pipeline.build_index()
    visible = permissions.visible(index.chunks, user["role"])
    allowed_numbers = crm.known_price_numbers() | scoring.numbers_in(c["text"] for c in visible)

    totals = {"answers": [0, 0], "recall": [0, 0], "summary": [0, 0]}
    report = {}
    for name in names:
        exp_all = json.loads((config.EXPECTED / f"{name}.json").read_text())
        rfp_text = (config.RFPS / f"{name}.txt").read_text()
        report[name] = {}
        for n in range(1, args.runs + 1):
            print(f"\n=== {name}  run {n}  ({user['name']}, {user['role']}, retrieval={args.mode}) ===")
            customer, requirements, recovered = pipeline.extract_requirements(rfp_text, log=lambda *_: None)
            got = {r["id"]: r for r in requirements}
            if recovered:
                print(f"  EXTRACTION missed {sorted(recovered)}; recovered by the code check")
            missing = sorted(set(exp_all["requirements"]) - set(got))
            if missing:
                print(f"  EXTRACTION missed (not recovered): {missing}")
            reqs = [got[i] for i in exp_all["requirements"] if i in got]
            rows = {r["id"]: r for r in pipeline.assess_requirements(reqs, index, user, use_library=False,
                                                                    log=lambda *_: None, recovered=recovered)}
            for rid, exp in exp_all["requirements"].items():
                if rid not in rows:
                    fails, hit = ["not extracted"], False
                else:
                    fails, hit = scoring.score_requirement(exp, rows[rid]), scoring.recall_hit(exp, rows[rid]["searched"])
                totals["answers"][0] += not fails
                totals["answers"][1] += 1
                totals["recall"][0] += hit
                totals["recall"][1] += 1
                report[name].setdefault(rid, []).append(not fails)
                print(f"  {rid:<5} {'PASS' if not fails else 'FAIL'}  recall {'ok  ' if hit else 'MISS'} "
                      f"{'; '.join(fails)}")
            if not args.no_summary:
                header = "\n".join(rfp_text.splitlines()[:4])
                customer = customer or exp_all["customer"]
                summary, calls = summary_agent.run(header, customer, list(rows.values()), user, log=lambda *_: None)
                fails = scoring.score_summary(summary, calls, allowed_numbers)
                totals["summary"][0] += not fails
                totals["summary"][1] += 1
                print(f"  summary {'PASS' if not fails else 'FAIL'}  {'; '.join(fails)}  calls={calls}")

    print("\n=== Totals ===")
    for key, (ok, total) in totals.items():
        if total:
            print(f"  {key:<8} {ok}/{total}  ({100 * ok / total:.0f}%)")
    flaky = [f"{n}:{rid}" for n, reqs in report.items() for rid, res in reqs.items() if 0 < sum(res) < len(res)]
    if flaky:
        print(f"  flaky (passed in some runs only): {', '.join(flaky)}")
    config.OUTPUTS.mkdir(exist_ok=True)
    with open(config.OUTPUTS / "eval_history.jsonl", "a") as f:
        f.write(json.dumps({"time": datetime.now().isoformat(timespec="seconds"), "rfps": names,
                            "runs": args.runs, "user": args.user, "mode": args.mode, "model": config.MODEL,
                            "totals": totals}) + "\n")


if __name__ == "__main__":
    main()
