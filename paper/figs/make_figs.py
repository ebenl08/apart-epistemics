"""Paper figures with 95% bootstrap CIs over trials. Run from repo root: python3 paper/figs/make_figs.py"""
import re
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, "infra/semantic_entropy")
from analyze import LEVELS, ci95  # reuse: same CI as the lab-note figures

N = Path(".agent/notes/figs"); OUT = Path("paper/figs")
plt.rcParams.update({"font.size": 8, "axes.titlesize": 8, "axes.labelsize": 8, "legend.fontsize": 7,
                     "xtick.labelsize": 7, "ytick.labelsize": 7})
FAM = {"kv-store": "KV store", "log-triage": "LogTriage"}
MODELS = {"qwen35-4b": ("4B", "C2"), "qwen35-9b": ("9B", "C0"), "qwen35-9b-rl": ("9B-RL", "C1")}


def md_table(path):
    rows = [[c.strip() for c in l.strip().strip("|").split("|")] for l in open(path) if l.startswith("| ")]
    df = pd.DataFrame(rows[1:], columns=rows[0])
    df["reward"] = df.reward.astype(float)
    df["fam"] = df.task.str.extract(r"^(kv-store|log-triage)")[0]
    df["level"] = df.task.str.extract(r"-(R\d+|L\d+)-seed")[0]
    return df


def save(fig, name):
    fig.tight_layout(rect=(0, .08, 1, 1)) if name == "exp1-reward" else fig.tight_layout(); fig.savefig(OUT / f"{name}.pdf"); fig.savefig(OUT / f"{name}.png", dpi=200); plt.close(fig)


def exp1():
    clm, none = md_table(N / "m5-combined.md"), md_table(N / "m5-none.md")
    fig, axes = plt.subplots(1, 2, figsize=(5.5, 2.3), sharey=True)
    for a, fam in zip(axes, LEVELS):
        for m, (lab, col) in MODELS.items():
            for df, ls, alpha, off in ((clm, "-", 1, 0), (none, "--", .35, .05)):
                d = df[(df.model == m) & (df.fam == fam)]
                if d.empty:
                    continue
                y = [d[d.level == l].reward.mean() for l in LEVELS[fam]]
                e = np.array([ci95(d[d.level == l].reward) for l in LEVELS[fam]]).T
                x = np.arange(4) + (list(MODELS).index(m) - 1) * .07 + off
                a.errorbar(x, y, yerr=e, ls=ls, marker="o", ms=3, capsize=2, color=col, alpha=alpha,
                           label=lab if ls == "-" else None)
        a.set_xticks(range(4)); a.set_xticklabels(LEVELS[fam]); a.set_title(FAM[fam]); a.set_xlabel("pressure level")
    axes[0].set_ylabel("mean reward"); axes[0].set_ylim(-.05, 1.08)
    axes[1].plot([], [], "k--", alpha=.35, label="skill=none")
    fig.legend(*axes[1].get_legend_handles_labels(), loc="lower center", ncol=4, frameon=False, bbox_to_anchor=(.5, -.02))
    save(fig, "exp1-reward")
    return clm


def exp2():
    # rows: SE, reward; columns: KV store, LogTriage; lines: 9B, 9B-RL (same colours as exp1)
    fig, ax = plt.subplots(2, 2, figsize=(5.5, 3.6), sharex="col", layout="constrained")
    out = {}
    for k, (m, lab, colr) in enumerate((("m5-9b", "9B", "C0"), ("m5-9b-rl", "9B-RL", "C1"))):
        T = pd.read_csv(N / f"m6-se-trials-{m}.csv")
        T = T[~T.format_slip.astype(bool)]  # same exclusion as the H1 tests (one 9B-RL format slip)
        out[lab] = T
        for c, fam in enumerate(("kv-store", "log-triage")):
            g = T[T.family == fam].groupby("level"); x = np.arange(4) + (k - .5) * .08
            for r, col in enumerate(("mean_se", "reward")):
                ys = [g.get_group(l)[col].mean() for l in LEVELS[fam]]
                e = np.array([ci95(g.get_group(l)[col]) for l in LEVELS[fam]]).T
                ax[r, c].errorbar(x, ys, yerr=e, marker="o", ms=3, capsize=2, color=colr, label=lab)
    for c, fam in enumerate(("kv-store", "log-triage")):
        ax[0, c].set_title(FAM[fam]); ax[1, c].set_xlabel("pressure level")
        ax[1, c].set_xticks(range(4)); ax[1, c].set_xticklabels(LEVELS[fam])
        ax[0, c].set_ylim(0, .6); ax[1, c].set_ylim(-.05, 1.08)
    ax[0, 0].set_ylabel("mean trial SE (bits)"); ax[1, 0].set_ylabel("mean reward")
    ax[0, 0].legend(frameon=False, loc="upper left")
    fig.savefig(OUT / "exp2-se.pdf", bbox_inches="tight"); fig.savefig(OUT / "exp2-se.png", dpi=200, bbox_inches="tight")
    return out


if __name__ == "__main__":
    clm = exp1()
    t = clm.groupby(["model", "fam", "level"]).reward.agg(["mean", "size"]).round(2)
    print(t.to_string())
    for lab, T in exp2().items():
        print(lab, len(T), T.groupby(["family", "level"])[["reward", "mean_se"]].mean().round(2).to_string(), sep="\n")
