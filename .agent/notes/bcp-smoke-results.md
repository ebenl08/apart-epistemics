# BCP smoke test results (BrowseComp-Plus, 5 questions)

Date: 2026-11-14. Started 18:23 UTC. Status: **done** 18:30 UTC (all 5 trials finished in 17 s to 7.4 min).
Plan: [`../instruction-reimplementation.md`](../instruction-reimplementation.md) (M4, smoke).
Raw trials: `runs/bcp-smoke/trials/` (gitignored). Utilization: `runs/logs/util-bcp-smoke-m2.csv`.
Runs concurrently with M2 KV ([`m2-kv-results.md`](m2-kv-results.md)) on the same vLLM server.

## Setup (control unless marked)

- Model: Qwen3.5-4B BF16, vLLM 0.33.0 (shared server, `infra/serve_qwen35_4b.sh`).
- Agent: `ClmAgent` with [`bcp.yaml`](../../context-language-models/clm/clm_harness/configs/bcp.yaml):
  max_steps 500, T=0.7, budget 28672 / reserve 2048, nudges 0.25/0.5/0.75 + persistent 0.9,
  finalize nudges 3.
- **Changed vs bcp.yaml:** `cost_metric=usd` (bcp.yaml's FLOPs key is for 27B; 4B
  `flops_n_body` not set).
- Search skill `infra/bcp/skill/bcp_search` (BM25, top-10, 512-token snippets, 8192-token
  reader), server on :8100. Sandbox: proot (`infra/chroot_env.py`); :8100 reachable from proot (checked).
- Questions: 624, 1204, 679, 69, 427 (from `data/bcp/sample_seed0_n50.json`).
- Grading: provisional substring grader only. **No LLM judge** (user decision 2026-11-14:
  skip the judge this sprint; answers are kept in `/app/answer.md` for later judging).
- Instruction and SKILL.md are our own wording (deviation; paper's BCP prompt not in repo).

## Results

| QID | reward (substring) | answered | steps / LM calls | edits | peak ctx | terminated |
|---|---|---|---|---|---|---|
| 427 | 0 | no | 1 / 1 | 0 | 2.1k | gave up: submitted on the first call without searching |
| 624 | 0 | no | 22 LM calls, 12 kept | 0 | ~28k (budget) | budget exhausted after 6/6 rollbacks (3 min) |
| 1204 | 0 | no | 20 LM calls, 9 kept | 0 | ~27k (budget) | budget exhausted after 6/6 rollbacks (5 min) |
| 679 | 0 | no | 52 LM calls, 12 kept | 1 real, 1 rejected | ~29k (budget) | budget exhausted after 6/6 rollbacks (7.4 min) |
| 69 | 0 | no | 22 LM calls, 13 kept in trajectory | 0 | 28.6k (budget) | budget exhausted after 6/6 rollbacks; ignored the final-turn notice (searched again) |

## Observations

- 427: the model reasoned the question was too hard and ran
  `echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT` immediately. Model behavior, not a pipeline bug.
- Harmless proot warning in every command: host cwd absent in guest, falls back to `/`.
- 69 hit the context limit early and rolled back (`rollback_retry`), so budget handling is active.
- 69 (finished 18:25, 2.5 min): **no context edits at all** (`n_ctx_syncs_real 0`) despite 3 nudges.
  Each `search` returns ~10 x 512-token snippets (~4-5k tokens), so the 28.6k budget holds
  only ~4-5 searches. The model kept issuing ever-shorter keyword searches (`search "ugly"`,
  `search "trolled"`), hit the limit, was rolled back 6 times, then on the FINAL-turn notice
  searched again instead of writing `/app/answer.md`. Same pattern as M1 `skill=none`:
  without a method text, 4B does not offload; BCP gets only the search skill.
- 624: same failure as 69. 0 edits, 3 nudges ignored, one `get_document`, then single-word
  searches (`search "coffee"`, `search 'Colombia'`) until 6/6 rollbacks. Ended without an answer.
- 1204: same failure. 0 edits, 8 nudges ignored. Searches were on target (identified the
  topic as Zelda / Ocarina of Time, was narrowing to Link's voice actor) but it never wrote
  a provisional answer before the budget ran out. Best candidate for a fix: it was close.
- 679: the only trial that touched its context: one Python edit of `LIVE_CTX_MAIN.txt`
  (1 accepted, 1 rejected), then back to searching (Purdue / Murphy award / Crossley) until
  6/6 rollbacks. 9 nudges. No answer.

## Summary

**0/5 answered, 0/5 correct.** The pipeline works end to end (search server reachable
from proot, `search` / `get_document` called correctly, nudges and rollbacks fire,
verifier writes `reward.json`). The model is the bottleneck:

1. **No offloading.** 4 of 5 trials made 0 context edits; 679 made 1. Same as M1 with
   `skill=none`: 4B does not edit context without a method text, and BCP gets only the
   search skill. Compare KV, where `skill=clm` gives 1 edit per batch and 24/24 at R1000.
2. **Search results flood the budget.** ~4-5k tokens per `search` (10 x 512-token snippets)
   vs a 28.6k budget: ~5 searches before the wall. Rollbacks then loop the model.
3. **No answer under pressure.** None wrote a provisional `/app/answer.md`, even on the
   FINAL-turn notice (69 searched again). 427 quit at call 1.
4. Query quality degrades into single keywords (`search "ugly"`, `search 'Colombia'`).
   1204 was on the right track (Zelda / Ocarina of Time) when the budget ran out.

**Implication for M4 (50 q):** as configured, expect ~0%. Options (need user decision):
(a) a BCP method text (offload search results to a notes file, keep a running candidate
answer) — our addition, not the paper's; (b) `k=3-5` / shorter snippets — deviates from
the plan's top-10 x 512; (c) instruct "write a provisional answer early"; (d) run as-is
and report 4B as below floor.
