"""H3 decision level: does ablating the SE direction change semantic entropy at the same decision points?

Each condition dir (runs/m6-h3/<cond>/) holds per-point results for the 9B decision points, sampled from the
edited model with the same per-point seeds as the baseline (runs/m6-se/m5-9b__*.jsonl). Paired by (trial, t).
SE is recomputed from the stored sample keys, three ways:
  plain  = first 10 samples (the pre-registered K = 10);
  valid  = those 10 minus every non-ok status (format failures and non-zero-exit `invalid`);
  rs     = first 10 samples with a valid tool call (rejection sampling; `invalid` kept, it is a decision).
Usage: [H3_QUEUE=runs/m6-se/queue-<q>.txt] python h3_analyze.py <out.md> <cond> [<cond> ...]
"""
from __future__ import annotations

import glob
import json
import os
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon

from entropy import se_bits

ROOT = Path("/workspace/apart-epistemics/runs")
FMT = ("no_tool_call", "context_status", "error")        # tool-call format / harness failures
STATUS = FMT + ("invalid",)
K = 10


def _se(keys: list[str], min_n: int = 2) -> float:
    return se_bits(list(Counter(keys).values())) if len(keys) >= min_n else np.nan


def load(d: Path, trials: set[str] | None, prefix: str = "m5-9b") -> pd.DataFrame:
    rows = [json.loads(x) for f in sorted(glob.glob(str(d / f"{prefix}__*.jsonl")))
            if not f.endswith(".samples.jsonl") for x in open(f)]
    df = pd.DataFrame(rows)
    if trials is not None:
        df = df[df.trial.isin(trials)]
    df = df.set_index(["trial", "t"])
    keys = df.samples.apply(lambda ss: [x["key"] for x in ss])
    df["keys10"] = keys.apply(lambda k: k[:K])
    df["se_plain"] = df.keys10.apply(_se)
    df["se_valid"] = df.keys10.apply(lambda k: _se([x for x in k if x not in STATUS]))
    rs = keys.apply(lambda k: [x for x in k if x not in FMT][:K])
    df["se_rs"] = [(_se(k) if len(k) == K else np.nan) for k in rs]   # NaN: cap reached before 10 valid calls
    df["n_total"] = keys.apply(len)
    return df


def summary(df: pd.DataFrame) -> dict:
    k = df.keys10.explode()
    return {"points": len(df), "SE plain": df.se_plain.mean(), "SE valid-only": df.se_valid.mean(),
            "SE rejection-sampled": df.se_rs.mean(), "points with 10 valid calls": df.se_rs.notna().mean(),
            "share SE > 0": (df.se_plain > 0).mean(),
            **{f"{s} (of first 10)": (k == s).mean() for s in STATUS},
            "agree with logged": np.mean([np.mean([x == lk for x in ks]) for ks, lk in zip(df.keys10, df.logged_key)]),
            "mean samples drawn": df.n_total.mean()}


def main() -> None:
    out, conds = Path(sys.argv[1]), sys.argv[2:]
    q = os.environ.get("H3_QUEUE")
    trials = {Path(x.strip()).stem for x in open(q) if x.strip()} if q else None
    base = load(ROOT / "m6-se", trials)
    rows = {"baseline (9B)": summary(base)}
    tests = []
    for c in conds:
        df = load(ROOT / "m6-h3" / c, trials)
        rows[c] = summary(df)
        for col, name in (("se_plain", "plain K = 10"), ("se_valid", "valid only"), ("se_rs", "rejection-sampled")):
            j = base[[col]].join(df[[col]], rsuffix="_c", how="inner").dropna()
            if j.empty:
                continue
            diff = j[col + "_c"] - j[col]
            p = wilcoxon(j[col + "_c"], j[col], zero_method="zsplit").pvalue if (diff != 0).any() else 1.0
            pt = j.groupby(level="trial").mean()
            dt = pt[col + "_c"] - pt[col]
            boot = [dt.sample(len(dt), replace=True, random_state=i).mean() for i in range(2000)]
            tests.append(f"| {c} | {name} | {len(j)} | {len(dt)} | {diff.mean():+.3f} | {p:.2g} | {dt.mean():+.3f} "
                         f"[{np.percentile(boot, 2.5):+.3f}, {np.percentile(boot, 97.5):+.3f}] | {(dt > 0).sum()}/{len(dt)} |")
    lines = ["# H3 decision level: directional ablation vs baseline (9B)", "",
             f"Trials: {'subset ' + q if q else 'all'}.", "",
             "## Outcomes per condition", "", pd.DataFrame(rows).T.round(3).to_markdown(), "",
             "## Paired change in SE vs baseline (same points, same seeds for the first 10 samples)", "",
             "| condition | SE | points | trials | mean ΔSE per point | Wilcoxon p | mean ΔSE per trial [95% CI] | trials up |",
             "|---|---|---|---|---|---|---|---|", *tests, ""]
    out.write_text("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
