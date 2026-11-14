# Handoff (temporary): CLM reimplementation, M1 done, BCP smoke in progress

Session: reimplementation. Updated: 2026-11-14 17:59 UTC.
Plan: [`../instruction-reimplementation.md`](../instruction-reimplementation.md).
Decisions: [`../decisions.md`](../decisions.md) (all of today's entries).
M1 results: [`../notes/m1-smoke-results.md`](../notes/m1-smoke-results.md).

## Where things stand

- **M1 (ContextBench smoke) done.** Go for **Qwen3.5-4B with `skill=clm`**. Without the
  skill, neither 4B nor 9B edits its context. The plan's App. F no-skill comparison
  (22.3 / 45.3) is replaced by the paper's CLM condition (`skill=clm`).
- **Now: BCP smoke test** (user's request before M2/M3), 5 questions, 4B, `bcp.yaml`.
  Everything is built; the BM25 index was still building at handoff time.
- **Not started:** M2 (KV), M3 (Sudoku), the full 50-question BCP run (M4), the judge.
- Nothing committed. `git status`: `.agent/decisions.md`, `.gitignore` modified;
  `.agent/notes/m1-smoke-results.md`, `infra/` untracked. Ask before committing (AGENT.md).

## Host (RunPod container)

- 1x A40 46 GB, 96 cores, 503 GB RAM. No Docker, no CAP_SYS_ADMIN.
- `/workspace` = persistent **quota-limited volume** (writes failed at ~54 GB; now ~27 GB
  used, `/workspace/.cache/uv` alone is 19 GB). `/` = container disk, 50 GB, **12 GB free**,
  lost if the pod is re-created.
- Large things live on `/`: venvs `/root/envs/{vllm-env,clm-env}`, HF cache
  `/root/hf_cache` (symlinked from `/workspace/.cache/huggingface`; Qwen3.5-4B + 9B,
  27 GB), rootfs template `/root/rootfs/py312slim`, per-trial roots `/root/chroots/`,
  BCP index `/root/bcp_index/`.
- If the pod was re-created: re-create the venvs (`uv venv` + `uv pip install vllm==0.33.0`;
  `uv pip install -e context-language-models -e "data/ContextBench[tokenizer]" pyarrow
  pandas bm25s PyStemmer`), `apt-get install proot`, re-download weights, re-pull the
  rootfs (registry script is in this session's history: Docker Hub token, amd64
  manifest of `python:3.12-slim`, untar layers; digest in `/root/rootfs/py312slim.digest`),
  and rebuild the BCP index.

## Layout (repo root)

| Path | What |
|---|---|
| `infra/chroot_env.py` | Harbor env `chroot_env:ChrootEnvironment`: per-trial copy of the rootfs, commands run under **proot** with host `/proc`, `/dev`, `/sys` bound (`CHROOT_RUNNER=chroot` = old fallback) |
| `infra/serve_qwen35_{4b,9b}.sh` | vLLM 0.33.0 servers on :8000 (`qwen35-4b` / `qwen35-9b`), 65k ctx, `--language-model-only`, parsers qwen3_coder/qwen3 |
| `infra/run_cb_trial.sh` | one ContextBench trial: `MODEL=qwen35-4b SKILL=clm infra/run_cb_trial.sh <task> <trials-dir>` |
| `infra/cb_status.py` | per-trial status line (ops, calls, terminated_by, reward) |
| `infra/bcp/prepare_queries.py` | decrypts queries -> `data/bcp/queries_decrypted.jsonl`, 50-id sample (seed 0) -> `data/bcp/sample_seed0_n50.json` (done) |
| `infra/bcp/build_index.py` | bm25s index -> `/root/bcp_index/{docs.parquet,bm25/}` (was running at handoff; log `runs/logs/bcp-index.log`) |
| `infra/bcp/search_server.py` | BM25 HTTP service on :8100 (`/search`, `/doc`, `/health`); top-10, 512-token snippets, 8192-token reader |
| `infra/bcp/skill/bcp_search/` | skill mounted via `skill_dirs`: `search "<q>" [k]`, `get_document <docid>`, `SKILL.md` |
| `infra/bcp/build_tasks.py` | Harbor tasks -> `data/bcp_tasks/bcp-<qid>/`; provisional substring grader; 5 built (624, 1204, 679, 69, 427) |
| `infra/run_bcp_trial.sh` | one BCP trial via the repo's `run_harbor.sh ... bcp`, + skill, `cost_metric=usd` |
| `data/` (gitignored) | `ContextBench/` (fb533c1), `cb_tasks/` (KV + Sudoku, seeds 42/43, timeout 28800), `bcp/` (corpus, queries, decrypted) |
| `runs/` (gitignored) | `m1/`, `m1b-4b-clm/`, `m1b-9b-none/` trials; `logs/` |

## Running at handoff

- vLLM **4B** server on :8000 (`nohup infra/serve_qwen35_4b.sh > runs/logs/vllm-serve-4b.log`).
- BM25 index **finished** (350 s): `/root/bcp_index/bm25` 746 MB + `docs.parquet` 1.7 GB.
  `/` has 11 GB free. Search server not started yet.
- Kill vLLM by its python pid (`pgrep -f "envs/vllm-env/bin/python.*vllm serve"`), never
  `pkill -f "vllm serve"` (it kills the calling shell).

## Next steps

1. Start the search server (index is built):
   `source /root/envs/clm-env/bin/activate && nohup python infra/bcp/search_server.py > runs/logs/bcp-search.log 2>&1 &`.
   Test with `curl 'localhost:8100/search?q=grizzly+bear+connectivity+model'`.
2. List the BCP smoke config (AGENT.md), then launch the 5 trials:
   `for q in 624 1204 679 69 427; do nohup infra/run_bcp_trial.sh $q runs/bcp-smoke/trials > runs/bcp-smoke/$q.log 2>&1 & done`.
   Check: tool use of `search`/`get_document`, edits under the `shrink` gate, nudge
   reactions, `/app/answer.md` written, `verifier/reward.json`. Note: whether the
   sandbox reaches :8100 from proot is untested (no network isolation, so it should).
3. Report to the user and stop (milestone rule). Then M2/M3 with `SKILL=clm`.

## Open items / decisions pending

- **ContextBench kwargs for M2/M3**: the plan's App. F overrides (32000 / 4096 / 240
  steps) were tied to the no-skill comparison. With `skill=clm`, `PAPER_KWARGS` as-is
  (32768 / 2048, no step cap) match the paper's CLM rows. Confirm with the user.
- Levels: KV R260 / R1000 / R4000 / R16000; Sudoku t8 / t30 / t60 / t150 (decided).
- 4B+clm Sudoku t8 scored 0/8 from one dropped first move (in-place sketchpad); watch it.
- BCP judge (Qwen3.5-27B-GPTQ-Int4) needs a GPU swap and ~20 GB disk. `/` has 12 GB
  free: freeing the 9B weights (18 GB) or the uv cache needs the user's OK.
- BCP FLOPs: `bcp.yaml` uses `flops_model_key: 27b`; smoke uses `cost_metric=usd`.
  The plan wants `flops_n_body` for 4B (not set yet).
- BCP instruction and SKILL.md are our own wording (BCP-style answer format with
  Confidence); the paper's exact BCP prompt is not in the repo. Log as a deviation.
- The status updates every 3-5 min are done with Monitor loops around `infra/cb_status.py`.
