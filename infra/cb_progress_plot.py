"""Plot how far each arm gets through the stream (ops done / ops total) against pressure, from cb_report tables.
Useful when rewards are all ~0 (skill=none): progress before the budget wall still separates the arms.
Usage: python infra/cb_progress_plot.py --out <prefix> --title <t> <table.md> [...]  (arms = model / skill)
"""
import argparse
import re
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ap = argparse.ArgumentParser()
ap.add_argument("--out", required=True); ap.add_argument("--title", default="")
ap.add_argument("--models", nargs="*", help="keep only these model names")
ap.add_argument("tables", nargs="+")
a = ap.parse_args()
cells = defaultdict(list)  # (family, arm, level) -> [(pressure, frac)]
for t in a.tables:
    for l in open(t):
        c = [x.strip() for x in l.split("|")[1:-1]]
        if len(c) != 13 or c[0] not in ("kv_store", "log_triage") or "/" not in c[7]:
            continue
        if a.models and c[1] not in a.models:
            continue
        done, tot = map(int, c[7].split("/"))
        lvl = re.search(r"-(R\d+|L\d+)-", c[3]).group(1)
        cells[(c[0], f"{c[1]} / {c[2]}", lvl)].append((float(c[4]), done / tot))
fams = ["kv_store", "log_triage"]
arms = sorted({k[1] for k in cells})
colors = {"4b": "#2563eb", "9b": "#dc2626", "9b-rl": "#16a34a"}
fig, axes = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
for ax, fam in zip(axes, fams):
    for arm in arms:
        pts = sorted((sum(p for p, _ in v) / len(v), [f for _, f in v]) for (f_, a_, _), v in cells.items()
                     if f_ == fam and a_ == arm)
        if not pts:
            continue
        m = arm.split(" / ")[0].replace("qwen35-", "")
        style = dict(color=colors.get(m, "gray"), ls="-" if arm.endswith("clm") else "--")
        ax.plot([p for p, _ in pts], [sum(f) / len(f) for _, f in pts], marker="o", label=arm, **style)
        for p, fs in pts:
            ax.scatter([p] * len(fs), fs, s=10, alpha=0.35, color=style["color"])
    ax.set_xscale("log"); ax.axvline(1, color="gray", ls=":", lw=1); ax.set_ylim(-0.03, 1.05)
    ax.set_title(fam); ax.set_xlabel("pressure (input / budget)"); ax.grid(alpha=0.3)
axes[0].set_ylabel("stream ops completed (fraction)")
axes[0].legend(frameon=False, fontsize=8)
fig.suptitle(a.title, fontsize=10); fig.tight_layout()
fig.savefig(a.out + ".png", dpi=130)
print("wrote", a.out + ".png")
