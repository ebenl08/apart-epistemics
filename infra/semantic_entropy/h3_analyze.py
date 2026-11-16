"""H3 decision level: does ablating the SE direction change semantic entropy at the same decision points?

Each condition dir (runs/m6-h3/<cond>/) holds per-point results for the 9B decision points, sampled from the
edited model with the same per-point seeds as the baseline (runs/m6-se/m5-9b__*.jsonl). Paired by (trial, t).
Usage: python h3_analyze.py <out.md> <cond> [<cond> ...]
"""
from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon

ROOT = Path("/workspace/apart-epistemics/runs")
STATUS = ("invalid", "no_tool_call", "context_status", "error")


def load(d: Path, prefix: str = "m5-9b") -> pd.DataFrame:
    rows = [json.loads(x) for f in sorted(glob.glob(str(d / f"{prefix}__*.jsonl")))
            if not f.endswith(".samples.jsonl") for x in open(f)]
    return pd.DataFrame(rows).set_index(["trial", "t"])


def summary(df: pd.DataFrame) -> dict:
    ks_all = df.samples.apply(lambda ss: [x["key"] for x in ss])
    keys = ks_all.explode()
    return {"points": len(df), "mean SE": df.se_bits.mean(), "share SE > 0": (df.se_bits > 0).mean(),
            **{f"{s} samples": (keys == s).mean() for s in STATUS},
            "agree with logged": np.mean([np.mean([k == lk for k in ks]) for ks, lk in zip(ks_all, df.logged_key)])}


def main() -> None:
    out, conds = Path(sys.argv[1]), sys.argv[2:]
    base = load(ROOT / "m6-se")
    rows = {"baseline (9B)": summary(base)}
    lines = ["# H3 decision level: directional ablation vs baseline (9B)", ""]
    tests = []
    for c in conds:
        df = load(ROOT / "m6-h3" / c)
        rows[c] = summary(df)
        j = base[["se_bits"]].join(df[["se_bits"]], rsuffix="_c", how="inner")
        diff = j.se_bits_c - j.se_bits
        p = wilcoxon(j.se_bits_c, j.se_bits, zero_method="zsplit").pvalue if (diff != 0).any() else 1.0
        per_trial = j.groupby(level="trial").mean()
        dt = per_trial.se_bits_c - per_trial.se_bits
        boot = [dt.sample(len(dt), replace=True, random_state=i).mean() for i in range(2000)]
        tests.append(f"| {c} | {len(j)} | {diff.mean():+.3f} | {p:.2g} | {dt.mean():+.3f} "
                     f"[{np.percentile(boot, 2.5):+.3f}, {np.percentile(boot, 97.5):+.3f}] | {(dt > 0).sum()}/{len(dt)} |")
    t = pd.DataFrame(rows).T
    lines += ["## Outcomes per condition (share of samples unless stated)", "", t.round(3).to_markdown(), "",
              "## Paired change in SE vs baseline", "",
              "| condition | points | mean ΔSE per point | Wilcoxon p | mean ΔSE per trial [95% CI] | trials with ΔSE > 0 |",
              "|---|---|---|---|---|---|", *tests, ""]
    out.write_text("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
