"""M5B figure: reward and success vs context pressure, Qwen 3.5 9B (M5) vs Gemma 4 E4B vs Ministral 3 8B (skill=clm).

Usage: python3 infra/m5b_plot.py --out .agent/notes/figs/m5b <cb_report table.md> [...]
Reads cb_report.py per-trial tables (family, model, skill, task, pressure, seed, reward, ...). Two rows of panels:
mean reward with per-seed points, success rate (reward >= 0.95), and budget-wall rate (context hit the 32k budget before the
stream ended); one column per family.
"""
import argparse
import math
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

MODELS = [  # fixed categorical order (validated palette, light mode), marker as secondary encoding
    ("qwen35-9b", "Qwen 3.5 9B (M5, 8 seeds)", "#2a78d6", "o"),
    ("gemma4-e4b", "Gemma 4 E4B (4 seeds)", "#eb6834", "s"),
    ("ministral3-8b", "Ministral 3 8B (4 seeds)", "#1baf7a", "^"),
]
FAMS = [("kv_store", "KV store"), ("log_triage", "LogTriage")]
LEVELS = {"kv_store": ["R260", "R1000", "R4000", "R16000"], "log_triage": ["L320", "L1600", "L6400", "L12800"]}


def read(paths):
    rows = []
    for p in paths:
        hdr = None
        for line in open(p):
            if not line.startswith("|") or line.startswith("|---"):
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if hdr is None:
                hdr = cells
                continue
            r = dict(zip(hdr, cells))
            if r.get("skill") != "clm" or not r.get("reward"):
                continue
            try:
                r["reward"] = float(r["reward"])
            except ValueError:
                continue
            r["level"] = r["task"].split("-")[2]
            r["wall"] = r.get("end") == "budget_wall"
            rows.append(r)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("tables", nargs="+")
    a = ap.parse_args()
    rows = read(a.tables)
    cell, wall = defaultdict(list), defaultdict(list)
    for r in rows:
        cell[(r["model"], r["family"], r["level"])].append(r["reward"])
        wall[(r["model"], r["family"], r["level"])].append(r["wall"])

    plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False})
    fig, axes = plt.subplots(3, 2, figsize=(9, 8.6), sharex="col")
    ink, muted = "#2b2b2a", "#6b6b68"
    for ci, (fam, ftitle) in enumerate(FAMS):
        levels = LEVELS[fam]
        for ri, metric in enumerate(["mean reward", "success rate (reward ≥ 0.95)", "budget-wall rate"]):
            ax = axes[ri][ci]
            ends = []  # (y, label) of each line end, de-collided below
            for mi, (m, label, color, marker) in enumerate(MODELS):
                xs, ys = [], []
                for li, lv in enumerate(levels):
                    v = cell.get((m, fam, lv))
                    if not v:
                        continue
                    y = (sum(v) / len(v), sum(x >= 0.95 for x in v) / len(v),
                         sum(wall[(m, fam, lv)]) / len(v))[ri]
                    xs.append(li); ys.append(y)
                    if ri == 0:  # per-seed points, jittered per model
                        off = (mi - 1) * 0.09
                        ax.scatter([li + off] * len(v), v, s=10, color=color, alpha=0.35, linewidths=0, zorder=2)
                if not xs:
                    continue
                ax.plot(xs, ys, color=color, lw=2, marker=marker, ms=7, mec="#fcfcfb", mew=1.5, zorder=3, label=label)
                ends.append([ys[-1], label.split(" (")[0], xs[-1]])
            if ci == 1:  # direct labels at line ends (contrast relief), pushed apart by >= 0.08
                ends.sort()
                for k in range(1, len(ends)):
                    ends[k][0] = max(ends[k][0], ends[k - 1][0] + 0.08)
                for y, lab, x in ends:
                    ax.annotate(lab, (x, y), xytext=(8, 0), textcoords="offset points", va="center", fontsize=8, color=ink)
            ax.set_ylim(-0.04, 1.06)
            ax.set_xlim(-0.3, len(levels) - 1 + (0.9 if ci == 1 else 0.3))
            ax.set_xticks(range(len(levels)))
            ax.set_xticklabels(levels)
            ax.grid(axis="y", color="#e4e4e1", lw=0.8)
            ax.tick_params(colors=muted)
            if ci == 0:
                ax.set_ylabel(metric, color=ink)
            if ri == 0:
                ax.set_title(f"{ftitle} — pressure rises left to right", fontsize=10, color=ink)
    h, l = axes[0][0].get_legend_handles_labels()
    fig.legend(h, l, frameon=False, fontsize=8.5, ncol=3, loc="lower center", bbox_to_anchor=(0.5, 0.0))
    fig.suptitle("skill=clm: reward, success and budget walls vs context pressure", fontsize=11, color=ink)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(a.out + ".png", dpi=150, facecolor="#fcfcfb")
    print("wrote", a.out + ".png", len(rows), "trials")


if __name__ == "__main__":
    main()
