"""Build Harbor task dirs for sampled BrowseComp-Plus questions.

Usage: python build_tasks.py [--n N]   (first N of sample_seed0_n50.json; default 50)
Writes data/bcp_tasks/bcp-<query_id>/ (gitignored). The answer goes only into tests/,
which Harbor uploads after the agent has finished.

The verifier is provisional: normalized substring match of the gold answer in the
"Exact Answer:" line (reward_em). The plan's grader is the LLM judge
(Qwen3.5-27B-GPTQ-Int4, BCP grading template), run offline after all agent runs.
"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "bcp"
OUT = ROOT / "data" / "bcp_tasks"

INSTRUCTION = """# Deep research question

Answer the question below. You have no internet access; research it in the local
document corpus with the `search` and `get_document` tools described in your
system prompt. The corpus contains the documents needed to answer it.

## Question

{query}

## Output

When you are done, write your final response to `/app/answer.md` in exactly this format:

```
Explanation: {{your explanation for your final answer, citing the docids that support it}}
Exact Answer: {{your succinct, final answer}}
Confidence: {{your confidence score between 0% and 100% for your answer}}
```

If you cannot find the answer, still write your best guess in this format. Only
`/app/answer.md` is graded.
"""

TASK_TOML = """[metadata]
author_name = "apart-epistemics"
category = "deep-research"
tags = ["browsecomp-plus"]
bcp_query_id = "{qid}"

[verifier]
timeout_sec = 120.0

[agent]
timeout_sec = {agent_timeout}

[environment]
docker_image = "python:3.12-slim"
workdir = "/app"
build_timeout_sec = 600.0
cpus = 1
memory_mb = 2048
storage_mb = 4096
"""

TEST_SH = r"""#!/usr/bin/env bash
# Provisional grader: normalized substring match (LLM judge runs offline later).
mkdir -p /logs/verifier
cp /app/answer.md /logs/verifier/answer.md 2>/dev/null || true
python3 - <<'PY'
import json, re, pathlib
gold = json.load(open("/tests/gold.json"))["answer"]
p = pathlib.Path("/app/answer.md")
txt = p.read_text(errors="replace") if p.exists() else ""
m = re.search(r"Exact Answer:\s*(.*)", txt)
ans = m.group(1).strip() if m else ""
c = re.search(r"Confidence:\s*([0-9.]+)", txt)
norm = lambda s: re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()
em = float(bool(ans) and (norm(gold) in norm(ans) or norm(ans) == norm(gold)))
out = {"reward": em, "reward_em": em, "answered": float(bool(ans)),
       "confidence": float(c.group(1)) if c else -1.0}
json.dump(out, open("/logs/verifier/reward.json", "w"))
print(json.dumps(out))
PY
"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--agent-timeout", type=float, default=14400.0)
    args = ap.parse_args()
    rows = {r["query_id"]: r for r in map(json.loads, open(DATA / "queries_decrypted.jsonl"))}
    sample = json.loads((DATA / "sample_seed0_n50.json").read_text())[: args.n]
    for qid in sample:
        r = rows[qid]
        d = OUT / f"bcp-{qid}"
        (d / "tests").mkdir(parents=True, exist_ok=True)
        (d / "environment").mkdir(exist_ok=True)
        (d / "instruction.md").write_text(INSTRUCTION.format(query=r["query"].strip()))
        (d / "task.toml").write_text(TASK_TOML.format(qid=qid, agent_timeout=args.agent_timeout))
        t = d / "tests" / "test.sh"
        t.write_text(TEST_SH)
        t.chmod(0o755)
        (d / "tests" / "gold.json").write_text(json.dumps(
            {"query_id": qid, "answer": r["answer"], "gold_docids": r["gold_docids"],
             "evidence_docids": r["evidence_docids"]}, ensure_ascii=False))
    print(f"built {len(sample)} tasks in {OUT}: {sample}")


if __name__ == "__main__":
    main()
