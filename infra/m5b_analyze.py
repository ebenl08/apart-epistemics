"""M5B analysis: per-cell stats, trend tests, logistic comparison with Qwen (M5), LM-call behaviour, failure triage.

Usage: python3 infra/m5b_analyze.py <m5b table.md> <m5-combined table.md> <lmlog_summary.jsonl>
Tables are cb_report.py outputs. Prints markdown sections to stdout.
Success = reward >= 0.95; wall = terminated_by budget_wall (the context hit the 32k budget before the stream ended).
"""
import json
import math
import sys
from collections import Counter, defaultdict

import numpy as np
import statsmodels.formula.api as smf
import pandas as pd

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from cb_rules import cochran_armitage  # noqa: E402

LEVELS = {"kv_store": ["R260", "R1000", "R4000", "R16000"], "log_triage": ["L320", "L1600", "L6400", "L12800"]}
NAMES = {"qwen35-9b": "Qwen 3.5 9B", "qwen35-4b": "Qwen 3.5 4B", "qwen35-9b-rl": "Qwen 3.5 9B-RL",
         "gemma4-e4b": "Gemma 4 E4B", "ministral3-8b": "Ministral 3 8B"}


def read(path):
    rows, hdr = [], None
    for line in open(path):
        if not line.startswith("|") or line.startswith("|---"):
            continue
        c = [x.strip() for x in line.strip().strip("|").split("|")]
        if hdr is None:
            hdr = c
            continue
        r = dict(zip(hdr, c))
        if not r.get("reward"):
            continue
        r["reward"] = float(r["reward"])
        r["pressure"] = float(r["pressure"])
        r["level"] = r["task"].split("-")[2]
        r["wall"] = r["end"] == "budget_wall"
        a, b = (r["ops"].split("/") + ["", ""])[:2]
        r["ops_done"], r["ops_total"] = (int(a), int(b)) if a.isdigit() and b.isdigit() else (None, None)
        for k in ("edits", "LM calls", "peak ctx", "min"):
            try:
                r[k] = float(r[k])
            except (ValueError, KeyError):
                r[k] = None
        rows.append(r)
    return rows


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else float("nan")


def cell_table(rows, models, skill):
    out = ["| Family | Model | Level (pressure) | n | Mean reward | Success | Wall | Ops done (of total) | Edits / trial "
           "| LM calls / trial | Peak ctx | Minutes |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for fam in LEVELS:
        for m in models:
            for lv in LEVELS[fam]:
                c = [r for r in rows if r["model"] == m and r["family"] == fam and r["level"] == lv and r["skill"] == skill]
                if not c:
                    continue
                out.append(f"| {fam} | {NAMES[m]} | {lv} ({c[0]['pressure']:.1f}x) | {len(c)} | {mean([r['reward'] for r in c]):.2f} "
                           f"| {sum(r['reward'] >= 0.95 for r in c)}/{len(c)} | {sum(r['wall'] for r in c)}/{len(c)} "
                           f"| {mean([r['ops_done'] for r in c]):.1f} / {c[0]['ops_total']} | {mean([r['edits'] for r in c]):.1f} "
                           f"| {mean([r['LM calls'] for r in c]):.0f} | {mean([r['peak ctx'] for r in c]) / 1000:.1f}k "
                           f"| {mean([r['min'] for r in c]):.0f} |")
    return "\n".join(out)


def trends(rows, models):
    out = ["| Model | KV: success | KV z (p) | LogTriage: success | LogTriage z (p) |", "|---|---|---|---|---|"]
    for m in models:
        cells = []
        for fam in LEVELS:
            f = [r for r in rows if r["model"] == m and r["family"] == fam and r["skill"] == "clm"]
            z, p = cochran_armitage([math.log2(r["pressure"]) for r in f], [int(r["reward"] >= 0.95) for r in f])
            cells += [f"{sum(r['reward'] >= 0.95 for r in f)}/{len(f)}", f"{z:+.2f} ({p:.3g})"]
        out.append(f"| {NAMES[m]} | " + " | ".join(cells) + " |")
    return "\n".join(out)


def logit_vs(rows, ref, other):
    d = pd.DataFrame([{"s": int(r["reward"] >= 0.95), "lp": math.log2(r["pressure"]), "fam": r["family"],
                       "is_other": int(r["model"] == other)}
                      for r in rows if r["model"] in (ref, other) and r["skill"] == "clm"])
    fit = smf.logit("s ~ is_other * lp + C(fam)", d).fit(disp=0)
    i, mfx = "is_other:lp", "is_other"
    return (f"| {NAMES[other]} vs {NAMES[ref]} | {fit.params[i]:+.2f} (SE {fit.bse[i]:.2f}, p = {fit.pvalues[i]:.3g}) "
            f"| {fit.params[mfx]:+.2f} (p = {fit.pvalues[mfx]:.3g}) | {fit.params['lp']:+.2f} (p = {fit.pvalues['lp']:.3g}) | {len(d)} |")


def lm_behaviour(summary_path):
    by = defaultdict(Counter)
    per_trial = {}
    for line in open(summary_path):
        s = json.loads(line)
        f = s["file"]
        if "outage" in s["path"]:
            continue
        model = "gemma4-e4b" if f.startswith("m5b-gemma4-e4b") else "ministral3-8b"
        arm = "none" if "-none__" in f else "clm"
        k = (model, arm)
        c = s["calls"]
        by[k]["trials"] += 1
        by[k]["calls"] += len(c)
        by[k]["tool"] += sum(x.get("tc", False) for x in c)
        by[k]["no_tool"] += sum(1 for x in c if "tc" in x and not x["tc"])
        by[k]["empty"] += sum(x.get("empty", False) for x in c)
        by[k]["mirror"] += sum(x.get("mirror_text", False) for x in c)
        by[k]["fence"] += sum(x.get("fence_text", False) for x in c)
        by[k]["length"] += sum(x.get("fr") == "length" for x in c)
        by[k]["errors"] += sum("error" in x for x in c)
        by[k]["dropped"] += sum(x.get("dropped_empty", 0) > 0 for x in c)
        by[k]["completion_tokens"] += sum(x.get("completion_tokens") or 0 for x in c)
        by[k]["reasoning_chars"] += sum(x.get("reasoning_chars", 0) for x in c)
        by[k]["content_chars"] += sum(x.get("content_chars", 0) for x in c)
        per_trial[f] = s
    out = ["| Model / arm | Trials | LM calls | Native tool calls | No tool call | of which empty | of which `bash {…}` text "
           "| of which fenced text | Cut at max_tokens | HTTP errors | Completion tokens / call | Reasoning chars / call |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for (m, arm), c in sorted(by.items()):
        n = c["calls"] or 1
        out.append(f"| {NAMES[m]} / {arm} | {c['trials']} | {c['calls']} | {c['tool']} ({100 * c['tool'] / n:.1f}%) "
                   f"| {c['no_tool']} ({100 * c['no_tool'] / n:.1f}%) | {c['empty']} | {c['mirror']} | {c['fence']} "
                   f"| {c['length']} | {c['errors']} | {c['completion_tokens'] / n:.0f} | {c['reasoning_chars'] / n:.0f} |")
    return "\n".join(out), per_trial


def main():
    m5b, m5, summ = sys.argv[1:4]
    rows = read(m5b) + [r for r in read(m5) if r["model"] in ("qwen35-9b", "qwen35-4b", "qwen35-9b-rl")]
    print("## Per-cell (skill=clm)\n")
    print(cell_table(rows, ["qwen35-9b", "gemma4-e4b", "ministral3-8b"], "clm"))
    print("\n## Gemma none\n")
    print(cell_table(rows, ["gemma4-e4b"], "none"))
    print("\n## Trend tests (Cochran–Armitage, success vs log2 pressure, one-sided decreasing)\n")
    print(trends(rows, ["qwen35-9b", "qwen35-4b", "qwen35-9b-rl", "gemma4-e4b", "ministral3-8b"]))
    print("\n## Logistic: success ~ model × log2(pressure) + family\n")
    print("| Comparison | Interaction (slope difference) | Main effect | Reference slope | n |\n|---|---|---|---|---|")
    for ref in ("qwen35-9b", "qwen35-4b"):
        for o in ("gemma4-e4b", "ministral3-8b"):
            print(logit_vs(rows, ref, o))
    print("\n## LM-call behaviour\n")
    tbl, per_trial = lm_behaviour(summ)
    print(tbl)
    print("\n## Zero / partial reward trials that did not hit the wall (for diagnosis)\n")
    for r in sorted(rows, key=lambda r: (r["model"], r["task"])):
        if r["model"] in ("gemma4-e4b", "ministral3-8b") and r["reward"] < 0.95 and not r["wall"]:
            key = f"m5b-{r['model']}-{r['skill']}__{r['task']}.jsonl"
            s = per_trial.get(key)
            nt = sum(1 for x in s["calls"] if "tc" in x and not x["tc"]) if s else "?"
            print(f"- {r['model']} {r['skill']} {r['task']}: reward {r['reward']:.3f}, ops {r['ops']}, edits {r['edits']}, "
                  f"calls {r['LM calls']}, no-tool {nt}, end {r['end']}")
            if s:
                for t in s["tail"][-2:]:
                    print(f"    · fr={t['fr']} cmd={t['cmd'][-300:]!r} content={t['content'][-300:]!r}")


if __name__ == "__main__":
    main()
