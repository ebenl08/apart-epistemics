"""One-line-per-trial status of ContextBench trials under a trials dir.

Usage: python infra/cb_status.py <trials-dir> [--oneline]
Reads interactive_stream.json (ops delivered/total, terminated_by), counts context
snapshots, and result.json (reward) when the trial has finished.
"""
import json
import sys
from pathlib import Path


def _reward(result: dict):
    vr = result.get("verifier_result") or {}
    rewards = vr.get("rewards") or vr.get("reward") or {}
    return rewards


def status(trials_dir: Path) -> list[str]:
    rows = []
    for d in sorted(p for p in trials_dir.iterdir() if p.is_dir()):
        agent = d / "agent"
        try:
            s = json.loads((agent / "interactive_stream.json").read_text())
            ops = f"{s.get('n_ops_delivered')}/{s.get('n_ops_total')}"
            term = s.get("terminated_by")
        except Exception:
            ops, term = "?", None
        snaps = len(list((agent / "context_snapshots").glob("*"))) \
            if (agent / "context_snapshots").is_dir() else 0
        state = "running"
        extra = ""
        if (d / "result.json").exists():
            r = json.loads((d / "result.json").read_text())
            state = "FAILED" if (d / "exception.txt").exists() else "done"
            extra = f" reward={_reward(r)}"
        rows.append(f"{d.name}: {state} ops={ops} calls={snaps} term={term}{extra}")
    return rows


if __name__ == "__main__":
    rows = status(Path(sys.argv[1]))
    print(" | ".join(rows) if "--oneline" in sys.argv else "\n".join(rows))
