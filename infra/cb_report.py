"""Tabulate and plot ContextBench trials.

Usage: python infra/cb_report.py --out <prefix> <run-dir> [<run-dir> ...]
Each run dir holds trials/<task>/ (Harbor trial dirs). Writes <prefix>.md (one row per
trial, sorted by family / arm / pressure) and <prefix>.png (reward vs pressure, one panel
per family, one line per model+skill arm, mean over seeds with per-seed points).
Pressure is the task's contextbench_pressure (task.toml); arm = model + skill from the
trial config. Unfinished trials are listed as "running" and left out of the plot.
"""
from __future__ import annotations

import argparse
import json
import re
import tomllib
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TASKS = ROOT / "data" / "cb_tasks"
FAMILIES = ["kv_store", "log_triage", "needle_retention", "sudoku_sketchpad"]


def load_trial(d: Path) -> dict | None:
    cfg_p = d / "config.json"
    if not cfg_p.exists():
        return None
    cfg = json.loads(cfg_p.read_text())
    agent = cfg.get("agent", {})
    task = d.name
    meta = {}
    tp = TASKS / task / "task.toml"
    if tp.exists():
        meta = tomllib.loads(tp.read_text()).get("metadata", {})
    row = {
        "task": task,
        "family": meta.get("contextbench_family", "?"),
        "pressure": meta.get("contextbench_pressure"),
        "seed": int(m.group(1)) if (m := re.search(r"seed(\d+)", task)) else None,
        "model": (agent.get("model_name") or "?").split("/")[-1],
        "skill": (agent.get("kwargs") or {}).get("skill", "?"),
        "status": "running",
    }
    try:
        s = json.loads((d / "agent" / "interactive_stream.json").read_text())
        row["ops"] = f"{s.get('n_ops_delivered')}/{s.get('n_ops_total')}"
        row["terminated_by"] = s.get("terminated_by")
    except Exception:
        row["ops"], row["terminated_by"] = "?", None
    rp = d / "result.json"
    if rp.exists():
        r = json.loads(rp.read_text())
        rw = (r.get("verifier_result") or {}).get("rewards") or {}
        exc = r.get("exception_info")
        row.update(status="error" if exc and not rw else "done",
                   reward=rw.get("reward"), peak=rw.get("agent_peak_tokens"),
                   error=(exc or {}).get("exception_type") if exc else None,
                   started=r.get("started_at"), finished=r.get("finished_at"))
    try:
        u = json.loads((d / "agent" / "usage.json").read_text())
        row["edits"] = u.get("n_ctx_syncs_real")
        row["calls"] = u.get("n_lm_calls")
    except Exception:
        pass
    return row


def minutes(r):
    from datetime import datetime
    try:
        a = datetime.fromisoformat(r["started"].replace("Z", "+00:00"))
        b = datetime.fromisoformat(r["finished"].replace("Z", "+00:00"))
        return (b - a).total_seconds() / 60
    except Exception:
        return None


def fmt(x, nd=2):
    return "" if x is None else (f"{x:.{nd}f}" if isinstance(x, float) else str(x))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--title", default="ContextBench")
    ap.add_argument("runs", nargs="+")
    a = ap.parse_args()
    rows = []
    for rd in a.runs:
        for d in sorted((Path(rd) / "trials").glob("*")):
            if d.is_dir() and (r := load_trial(d)):
                r["run"] = Path(rd).name
                rows.append(r)
    rows.sort(key=lambda r: (FAMILIES.index(r["family"]) if r["family"] in FAMILIES else 9,
                             r["model"], r["skill"], r["pressure"] or 0, r["seed"] or 0))
    lines = [f"# {a.title}", "",
             "| family | model | skill | task | pressure | seed | reward | ops | edits | LM calls | peak ctx | min | end |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        end = r.get("error") or r.get("terminated_by") or r["status"]
        lines.append("| " + " | ".join([
            r["family"], r["model"], r["skill"], r["task"], fmt(r["pressure"]), fmt(r["seed"]),
            fmt(r.get("reward"), 3), r.get("ops", ""), fmt(r.get("edits")), fmt(r.get("calls")),
            fmt(r.get("peak"), 0) if r.get("peak") else "", fmt(minutes(r), 1) if r.get("finished") else "",
            str(end)]) + " |")
    Path(a.out + ".md").write_text("\n".join(lines) + "\n")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    done = [r for r in rows if r.get("reward") is not None and r["pressure"]]
    fams = [f for f in FAMILIES if any(r["family"] == f for r in done)]
    if not fams:
        print(f"wrote {a.out}.md (no finished trials to plot)")
        return
    fig, axes = plt.subplots(1, len(fams), figsize=(max(4.2 * len(fams), 6.5), 3.8), squeeze=False)
    colors = {}
    palette = ["#2563eb", "#dc2626", "#16a34a", "#9333ea", "#ea580c", "#0891b2"]
    for ax, fam in zip(axes[0], fams):
        arms = defaultdict(lambda: defaultdict(list))
        for r in done:
            if r["family"] == fam:
                arms[f"{r['model']} / {r['skill']}"][r["pressure"]].append(r["reward"])
        for arm, pts in sorted(arms.items()):
            c = colors.setdefault(arm, palette[len(colors) % len(palette)])
            xs = sorted(pts)
            ax.plot(xs, [sum(pts[x]) / len(pts[x]) for x in xs], "-o", color=c, label=arm, ms=5)
            for x in xs:
                ax.scatter([x] * len(pts[x]), pts[x], color=c, alpha=0.35, s=14)
        ax.axvline(1.0, color="#999", lw=0.8, ls="--")
        ax.set_xscale("log"); ax.set_ylim(-0.05, 1.05)
        ax.set_title(fam); ax.set_xlabel("pressure (input / budget)")
        ax.grid(alpha=0.3)
    axes[0][0].set_ylabel("reward")
    handles = {}
    for ax in axes[0]:
        for h, l in zip(*ax.get_legend_handles_labels()):
            handles[l] = h
    fig.legend(handles.values(), handles.keys(), loc="lower center", ncol=len(handles), frameon=False)
    fig.suptitle(a.title, fontsize=10)
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    fig.savefig(a.out + ".png", dpi=130)
    print(f"wrote {a.out}.md and {a.out}.png ({len(done)} finished / {len(rows)} trials)")


if __name__ == "__main__":
    main()
