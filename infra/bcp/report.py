"""Summarize a BCP run dir: per-question table + outcome plot.

Usage: python infra/bcp/report.py --out <prefix> <run-dir>
Reads <run-dir>/trials/bcp-*/ (result.json, agent/usage.json, verifier/answer.md) and the
gold answer from data/bcp_tasks/bcp-<qid>/tests/gold.json. Outcome per question:
correct / wrong answer / no answer (quit: <= 2 LM calls) / no answer (budget: context
rolled back 6/6 or other). Plot: outcome counts split by whether the model made any
real context edit.
"""
import argparse, json, re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", required=True)
    ap.add_argument("--title", default="BrowseComp-Plus"); ap.add_argument("run")
    a = ap.parse_args()
    rows = []
    for d in sorted((Path(a.run) / "trials").glob("bcp-*")):
        q = d.name[4:]
        if not (d / "result.json").exists():
            continue
        r = json.loads((d / "result.json").read_text())
        rw = (r.get("verifier_result") or {}).get("rewards") or {}
        u = json.loads((d / "agent/usage.json").read_text()) if (d / "agent/usage.json").exists() else {}
        gold = json.loads((ROOT / f"data/bcp_tasks/bcp-{q}/tests/gold.json").read_text())["answer"]
        ans = ""
        if (d / "verifier/answer.md").exists():
            m = re.search(r"Exact Answer:\s*(.*)", (d / "verifier/answer.md").read_text())
            ans = m.group(1).strip() if m else ""
        mins = (datetime.fromisoformat(r["finished_at"].replace("Z", "+00:00"))
                - datetime.fromisoformat(r["started_at"].replace("Z", "+00:00"))).total_seconds() / 60
        calls, edits = u.get("n_lm_calls") or 0, u.get("n_ctx_syncs_real") or 0
        if rw.get("reward") == 1.0: out = "correct"
        elif rw.get("answered") == 1.0: out = "wrong answer"
        elif calls <= 2: out = "no answer (quit)"
        else: out = "no answer (budget)"
        rows.append(dict(q=q, out=out, calls=calls, edits=edits, nudges=u.get("n_nudges"),
                         conf=rw.get("confidence"), mins=mins, ans=ans, gold=gold))
    L = [f"# {a.title}", "", "| qid | outcome | LM calls | edits | nudges | conf | min | answer | gold |",
         "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        L.append(f"| {r['q']} | {r['out']} | {r['calls']} | {r['edits']} | {r['nudges']} | "
                 f"{'' if r['conf'] in (None, -1.0) else int(r['conf'])} | {r['mins']:.1f} | "
                 f"{r['ans'][:60].replace('|', '/')} | {r['gold'][:60].replace('|', '/')} |")
    Path(a.out + ".md").write_text("\n".join(L) + "\n")
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    outs = ["correct", "wrong answer", "no answer (budget)", "no answer (quit)"]
    cols = ["#16a34a", "#ea580c", "#9ca3af", "#4b5563"]
    groups = [("made ≥1 context edit", [r for r in rows if r["edits"] > 0]),
              ("no context edit", [r for r in rows if r["edits"] == 0])]
    fig, ax = plt.subplots(figsize=(8.5, 3.2))
    for gi, (g, rs) in enumerate(groups):
        left = 0
        for o, c in zip(outs, cols):
            n = sum(r["out"] == o for r in rs)
            ax.barh(gi, n, left=left, color=c, label=o if gi == 0 else None)
            if n: ax.text(left + n / 2, gi, str(n), ha="center", va="center", color="white", fontsize=9)
            left += n
    ax.set_yticks([0, 1]); ax.set_yticklabels([f"{g} (n={len(rs)})" for g, rs in groups])
    ax.invert_yaxis(); ax.set_xlabel("questions")
    ax.legend(frameon=False, fontsize=8, ncol=2, loc="upper center", bbox_to_anchor=(0.5, -0.25))
    ax.set_title(a.title, fontsize=10); fig.tight_layout(); fig.savefig(a.out + ".png", dpi=130)
    n = len(rows); c = sum(r["out"] == "correct" for r in rows)
    print(f"wrote {a.out}.md/.png: {c}/{n} correct")


if __name__ == "__main__":
    main()
