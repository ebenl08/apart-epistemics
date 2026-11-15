"""M6 semantic entropy: pure functions (no I/O). Plan: .agent/instruction-semantic-entropy.md Step 1.

Run `PYTHONPATH=context-language-models/clm python3 infra/semantic_entropy/entropy.py` for the self-check.
"""
from __future__ import annotations

import math
from collections import Counter

from clm_harness.context_utils.context_string import _HEADER_RE

MIN_LINE = 8          # shorter lines (`}`, `PY`) match anywhere and carry no signal
OFFLOAD_FRAC = 0.9    # share of a removed block's lines that must appear in written files


def se_bits(counts: list[int]) -> float:
    n = sum(counts)
    return -sum(c / n * math.log2(c / n) for c in counts if c) + 0.0


def se_weighted_bits(weights: dict[str, float]) -> float:
    z = sum(weights.values())
    return -sum(w / z * math.log2(w / z) for w in weights.values() if w) + 0.0


def outcome_key(status: str, labels: list[str] | None = None, clobber: bool = False) -> str:
    if status != "ok":
        return status
    return "|".join(labels or []) + f"|C{int(clobber)}"


def cluster(keys: list[str]) -> dict[str, int]:
    return dict(Counter(keys))


def _norm(s: str) -> str:
    return " ".join(s.split())


def blocks(text: str) -> list[str]:
    """Bodies of the [[CTX_TURN n role=..]] blocks, in order."""
    ms = list(_HEADER_RE.finditer(text))
    return [text[m.end(): ms[i + 1].start() if i + 1 < len(ms) else len(text)] for i, m in enumerate(ms)]


def label_blocks(before: str, after: str, written: str) -> list[str]:
    """Per block of `before`: stay / edit / offload / delete (plan Step 1)."""
    after_n, written_n = _norm(after), _norm(written)
    out = []
    for body in blocks(before):
        lines = [_norm(l) for l in body.splitlines() if len(l.strip()) >= MIN_LINE]
        if _norm(body) in after_n:
            out.append("stay")
        elif not lines:
            out.append("delete")
        elif any(l in after_n for l in lines):
            out.append("edit")
        elif sum(l in written_n for l in lines) >= OFFLOAD_FRAC * len(lines):
            out.append("offload")
        else:
            out.append("delete")
    return out


TOY_BEFORE = """[[CTX_TURN 1 role=user]]
SET alpha = 1111 (keep this one)
SET beta = 2222 (keep this one)

[[CTX_TURN 2 role=tool]]
batch 0004: ERROR disk full on node-17
batch 0004: WARN retry scheduled for node-17

[[CTX_TURN 3 role=assistant]]
I will now look at the next operation in the stream."""

TOY_AFTER = """[[CTX_TURN 1 role=user]]
SET alpha = 1111 (keep this one)
SET beta = 2222 (keep this one)"""

TOY_WRITTEN = """batch 0004: ERROR disk full on node-17
batch 0004: WARN retry scheduled for node-17
"""

if __name__ == "__main__":
    assert se_bits([10]) == 0
    assert round(se_bits([5, 3, 2]), 2) == 1.49
    assert round(se_bits([6, 2, 1, 1]), 2) == 1.57
    assert round(se_bits([9, 1]), 2) == 0.47
    assert round(se_weighted_bits({"a": 2.0, "b": 2.0}), 2) == 1.0
    assert label_blocks(TOY_BEFORE, TOY_AFTER, TOY_WRITTEN) == ["stay", "offload", "delete"]
    # partial keep -> edit
    half = TOY_AFTER + "\n\n[[CTX_TURN 2 role=user]]\nbatch 0004: ERROR disk full on node-17"
    assert label_blocks(TOY_BEFORE, half, "") == ["stay", "edit", "delete"]
    assert outcome_key("ok", ["stay", "offload"], True) == "stay|offload|C1"
    assert outcome_key("invalid") == "invalid"
    assert cluster(["a", "a", "b"]) == {"a": 2, "b": 1}
    print("entropy self-check ok")
