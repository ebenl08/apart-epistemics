"""M5B decision rules over finished ContextBench trials (rules fixed in .agent/instruction-m5b.md).

  python infra/cb_rules.py trend <run-dir>       exit 0 if success falls with pressure (one-sided Cochran-Armitage
                                                 p < 0.05 on KV or LogTriage), else 1
  python infra/cb_rules.py none-smoke <run-dir>  exit 0 = keep 2 seeds (>= 13/16 score 0 and <= 2/16 edit), 1 = extend
  python infra/cb_rules.py selftest
Success = reward >= 0.95, as in M5.
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from cb_report import load_trial  # noqa: E402


def cochran_armitage(xs, ys):
    """One-sided test that y (0/1) falls as x rises. Returns (z, p); p small = decreasing."""
    n = len(ys); p = sum(ys) / n
    if p in (0, 1):
        return float("nan"), 1.0
    xm = sum(xs) / n
    t = sum((x - xm) * y for x, y in zip(xs, ys))
    z = t / math.sqrt(p * (1 - p) * sum((x - xm) ** 2 for x in xs))
    return z, 0.5 * math.erfc(-z / math.sqrt(2))  # normal CDF at z


def trials(run_dir):
    rows = [load_trial(d) for d in sorted((Path(run_dir) / "trials").glob("*")) if d.is_dir()]
    return [r for r in rows if r and r.get("reward") is not None and r.get("pressure")]


def trend(run_dir):
    rows, hit = trials(run_dir), False
    for fam in ("kv_store", "log_triage"):
        f = [r for r in rows if r["family"] == fam]
        if not f:
            continue
        z, p = cochran_armitage([math.log2(r["pressure"]) for r in f], [int(r["reward"] >= 0.95) for r in f])
        print(f"{fam}: n={len(f)} success={sum(r['reward'] >= 0.95 for r in f)} z={z:.2f} one-sided p={p:.3g}")
        hit |= p < 0.05
    print("DECREASING" if hit else "NOT_DECREASING")
    return 0 if hit else 1


def none_smoke(run_dir):
    rows = trials(run_dir)
    zero = sum(r["reward"] == 0 for r in rows); edit = sum((r.get("edits") or 0) > 0 for r in rows)
    keep = len(rows) > 0 and zero >= 13 / 16 * len(rows) and edit <= 2 / 16 * len(rows)
    print(f"n={len(rows)} zero={zero} with_edit={edit} -> {'KEEP_2_SEEDS' if keep else 'EXTEND_TO_4'}")
    return 0 if keep else 1


def selftest():
    xs = [math.log2(p) for p in (0.4, 1.5, 6, 24) for _ in range(8)]
    z, p = cochran_armitage(xs, [1] * 8 + [1] * 6 + [0] * 2 + [1] * 3 + [0] * 5 + [0] * 8)
    assert z < 0 and p < 0.001, (z, p)
    z, p = cochran_armitage(xs, [0, 1] * 16)
    assert p > 0.3, (z, p)
    print("selftest ok")
    return 0


if __name__ == "__main__":
    cmd = sys.argv[1]
    sys.exit(selftest() if cmd == "selftest" else {"trend": trend, "none-smoke": none_smoke}[cmd](sys.argv[2]))
