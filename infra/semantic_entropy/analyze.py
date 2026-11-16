"""M6 Part 2: does semantic entropy of context decisions predict ContextBench reward beyond pressure?

Plan: .agent/instruction-semantic-entropy.md Part 2 (unit = trial; go/no-go fixed in advance).
Usage: python analyze.py <run prefix, e.g. m5-9b> <out dir>
"""
from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import statsmodels.formula.api as smf  # noqa: E402
from scipy.stats import rankdata, spearmanr  # noqa: E402
from sklearn.metrics import roc_auc_score  # noqa: E402

OUT = Path("/workspace/apart-epistemics/runs/m6-se")
LEVELS = {"kv-store": ["R260", "R1000", "R4000", "R16000"], "log-triage": ["L320", "L1600", "L6400", "L12800"]}
rng = np.random.default_rng(0)


def load(prefix: str) -> pd.DataFrame:
    rows = [json.loads(x) for f in sorted(glob.glob(str(OUT / f"{prefix}__*.jsonl")))
            if not f.endswith((".samples.jsonl",)) for x in open(f)]
    return pd.DataFrame(rows)


def partial_spearman(x, y, level) -> float:
    """Spearman of x and y after rank-residualizing both on level dummies."""
    d = pd.get_dummies(level).to_numpy(float)
    def res(v):
        r = rankdata(v)
        beta, *_ = np.linalg.lstsq(d, r, rcond=None)
        return r - d @ beta
    return float(np.corrcoef(res(x), res(y))[0, 1])


def boot_ci(f, n, B=2000):
    vals = []
    for _ in range(B):
        i = rng.integers(0, n, n)
        try:
            v = f(i)
            if np.isfinite(v):
                vals.append(v)
        except Exception:  # noqa: BLE001
            pass
    return (float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))) if vals else (np.nan, np.nan)


def ci95(v, B=2000) -> tuple[float, float]:
    """(below, above) the mean: 95% bootstrap percentile CI of the mean. Stays inside the data range,
    unlike a t-interval, which matters for bounded, bimodal rewards with n = 4-6."""
    v = np.asarray(v, float)
    if len(v) < 2:
        return 0.0, 0.0
    m = np.random.default_rng(0).choice(v, (B, len(v))).mean(1)
    lo, hi = np.percentile(m, [2.5, 97.5])
    return float(v.mean() - lo), float(hi - v.mean())


def plot_trials(T: pd.DataFrame, outdir: Path, prefix: str) -> None:
    """Per-level mean SE and reward with 95% CI over trials; reward vs SE scatter."""
    fig, ax = plt.subplots(1, 3, figsize=(15, 4.2))
    for k, (fam, mk) in enumerate((("kv-store", "o"), ("log-triage", "s"))):
        g = T[T.family == fam].groupby("level")
        x = np.arange(4) + (k - .5) * .08          # small dodge so the bars do not overlap
        for a, col in ((ax[0], "mean_se"), (ax[1], "reward")):
            m = [g.get_group(l)[col].mean() for l in LEVELS[fam]]
            e = np.array([ci95(g.get_group(l)[col]) for l in LEVELS[fam]]).T
            a.errorbar(x, m, yerr=e, marker=mk, capsize=4, label=fam)
    for a, t in ((ax[0], "mean trial SE (bits), 95% CI"), (ax[1], "mean reward, 95% CI")):
        a.set_xticks(range(4)); a.set_xticklabels(["lvl1", "lvl2", "lvl3", "lvl4"]); a.set_title(t); a.legend()
    sc = ax[2].scatter(T.mean_se, T.reward, c=[LEVELS[f].index(l) for f, l in zip(T.family, T.level)],
                       cmap="viridis", s=[40 if w else 20 for w in T.wall])
    ax[2].set_xlabel("trial mean SE (bits)"); ax[2].set_ylabel("reward"); ax[2].set_title("reward vs SE (colour = level, big = wall)")
    plt.colorbar(sc, ax=ax[2])
    fig.tight_layout(); fig.savefig(outdir / f"m6-se-{prefix}.png", dpi=120)


def plot_fill(P: pd.DataFrame, outdir: Path, prefix: str) -> None:
    """Point SE vs fill, with mean SE ± 95% CI per 0.1 fill bin on top."""
    fig, a = plt.subplots(figsize=(6, 4))
    a.scatter(P.fill, P.se_bits, s=6, alpha=.3, color="grey")
    b = (P.fill * 10).clip(upper=9.999).astype(int)
    g = P.groupby(b).se_bits
    a.errorbar(g.mean().index / 10 + .05, g.mean(), yerr=np.array(g.apply(ci95).tolist()).T, color="C0", marker="o", capsize=4,
               label="bin mean, 95% CI")
    a.set_xlabel("context fill"); a.set_ylabel("point SE (bits)"); a.legend()
    a.set_title("point SE vs context fill"); fig.tight_layout(); fig.savefig(outdir / f"m6-se-fill-{prefix}.png", dpi=120)


def wall_of(trial: str) -> bool:
    run, task = trial.split("__")
    p = Path("/workspace/apart-epistemics/runs") / run / "trials" / task / "result.json"
    r = json.loads(p.read_text())["verifier_result"]["rewards"]
    return r.get("terminated_by_code") == 2


def main() -> None:
    prefix, outdir = sys.argv[1], Path(sys.argv[2])
    outdir.mkdir(parents=True, exist_ok=True)
    pts = load(prefix)
    pts["harmful"] = pts["logged_key"].str.contains(r"delete|\|C1$", regex=True)
    hi = pts[pts.fill >= .75].groupby("trial").se_bits.mean().rename("mean_se_hi")
    tr = pts.groupby("trial").agg(model=("model", "first"), family=("family", "first"), level=("level", "first"),
                                  seed=("seed", "first"), reward=("reward", "first"), n_points=("t", "size"),
                                  mean_se=("se_bits", "mean"), max_se=("se_bits", "max"),
                                  frac_se0=("se_bits", lambda s: float((s == 0).mean())),
                                  gate_b=("gate_b", lambda s: float(s.dropna().mean()) if s.notna().any() else np.nan),
                                  n_invalid=("n_invalid", "sum"), n_error=("n_error", "sum")).join(hi)
    tr["wall"] = [wall_of(t) for t in tr.index]
    tr["format_slip"] = (tr.reward == 0) & ~tr.wall
    tr["fl"] = tr.family + ":" + tr.level
    tr = tr.reset_index()
    lines = [f"# M6 Part 2: semantic entropy vs reward ({prefix})", "",
             f"{len(tr)} trials, {len(pts)} decision points, {int(pts.n_error.sum())} sample errors. "
             f"Format-slip trials (reward 0 without a wall), excluded from the tests: "
             f"{', '.join(tr.loc[tr.format_slip, 'trial']) or 'none'}.", ""]
    T = tr[~tr.format_slip].reset_index(drop=True)

    # --- per-cell table
    cell = T.groupby(["family", "level"]).agg(n=("trial", "size"), reward=("reward", "mean"), walls=("wall", "sum"),
                                              mean_se=("mean_se", "mean"), max_se=("max_se", "mean"),
                                              frac_se0=("frac_se0", "mean")).reset_index()
    cell["o"] = [LEVELS[f].index(l) for f, l in zip(cell.family, cell.level)]
    cell = cell.sort_values(["family", "o"]).drop(columns="o")
    lines += ["## Per cell (mean over trials)", "", cell.round(3).to_markdown(index=False), ""]

    # --- main test: partial Spearman, three summaries
    lines += ["## H1: partial Spearman ρ(trial SE, reward | pressure level), 95% bootstrap CI over trials", "",
              "| summary | n | ρ | 95% CI | raw ρ |", "|---|---|---|---|---|"]
    res = {}
    for col in ("mean_se", "max_se", "mean_se_hi"):
        D = T.dropna(subset=[col]).reset_index(drop=True)
        f = lambda i, D=D, col=col: partial_spearman(D[col].to_numpy()[i], D.reward.to_numpy()[i], D.fl.to_numpy()[i])
        rho = f(np.arange(len(D)))
        ci = boot_ci(f, len(D))
        res[col] = (rho, ci)
        lines.append(f"| {col} | {len(D)} | {rho:+.3f} | [{ci[0]:+.3f}, {ci[1]:+.3f}] | "
                     f"{spearmanr(D[col], D.reward).statistic:+.3f} |")
    lines.append("")

    # --- regression
    m0 = smf.ols("reward ~ C(fl)", T).fit()
    m1 = smf.ols("reward ~ mean_se + C(fl)", T).fit()
    lines += ["## Regression: reward ~ mean_SE + C(family:level)", "",
              f"- SE coefficient {m1.params['mean_se']:+.3f} (SE {m1.bse['mean_se']:.3f}, p = {m1.pvalues['mean_se']:.3f}); "
              f"ΔR² over level-only model = {m1.rsquared - m0.rsquared:+.3f} (R² {m0.rsquared:.3f} → {m1.rsquared:.3f}).", ""]

    # --- step level
    P = pts[~pts.trial.isin(tr.loc[tr.format_slip, "trial"])]
    E = P[P.turn_type == "context_edit_turn"]
    lines += ["## Step level", ""]
    for name, D, y in (("harmful logged edit (deleted, not offloaded, or clobbered a file) among edit turns", E, E.harmful),
                       ("point in a trial that hit the wall (all points)", P, P.trial.map(dict(zip(tr.trial, tr.wall))))):
        y = y.astype(int)
        if 0 < y.sum() < len(y):
            auc = roc_auc_score(y, D.se_bits)
            ci = boot_ci(lambda i, D=D, y=y: roc_auc_score(y.to_numpy()[i], D.se_bits.to_numpy()[i]), len(D))
            lines.append(f"- AUROC of point SE for {name}: **{auc:.3f}** [{ci[0]:.3f}, {ci[1]:.3f}] (n = {len(D)}, positives {y.sum()})")
            res.setdefault("auroc", []).append(auc)
        else:
            lines.append(f"- {name}: no contrast (positives {y.sum()}/{len(y)})")
    lines.append("")

    # --- go / no-go (fixed in the plan)
    go_rho = any(abs(r) >= .3 and (ci[0] > 0 or ci[1] < 0) for r, ci in (res[c] for c in ("mean_se", "max_se", "mean_se_hi")))
    harm_auc = res.get("auroc", [np.nan])[0]
    go = go_rho or (harm_auc >= .65)
    lines += ["## Go / no-go for Part 3 (fixed in advance)", "",
              f"- Any partial |ρ| ≥ 0.3 with CI excluding 0: **{go_rho}**",
              f"- Harmful-edit AUROC ≥ 0.65: **{harm_auc >= .65}** ({harm_auc:.3f})",
              f"- **Decision: {'GO' if go else 'NO-GO'}**", ""]

    plot_trials(T, outdir, prefix)
    plot_fill(P, outdir, prefix)
    lines += [f"Plots: `m6-se-{prefix}.png`, `m6-se-fill-{prefix}.png`. Error bars = 95% bootstrap CI of the mean.", ""]
    tr.to_csv(outdir / f"m6-se-trials-{prefix}.csv", index=False)
    (outdir / f"m6-se-{prefix}.md").write_text("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
