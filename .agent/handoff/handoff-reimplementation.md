# Handoff (temporary): CLM reimplementation, overnight runs (M2 KV/LogTriage/Needle, BCP)

Session: reimplementation. Updated: 2026-11-14 21:40 UTC (overnight, user asleep).
Plan: [`../instruction-reimplementation.md`](../instruction-reimplementation.md).
Decisions: [`../decisions.md`](../decisions.md). Overnight checklist (live status):
[`../notes/overnight-checklist.md`](../notes/overnight-checklist.md).

## Where things stand

User's overnight brief (18:45 UTC): run as many ContextBench evals as possible, BCP if it works,
smoke 4B/9B × skill none/clm, skip Sudoku if still problematic, write results + analysis +
plot after every run and commit, watch disk, push when done.

Results (all in `.agent/notes/`, each with a plot in `figs/`, all committed):

| Run | Note | Headline |
|---|---|---|
| Smoke grid 4B + 9B × none/clm | [`smoke-grid-results.md`](../notes/smoke-grid-results.md) | no-skill hits the wall on KV/LogTriage at 0.5x; 9B+clm 1.0 on all three |
| KV 4B + clm | [`m2-kv-results.md`](../notes/m2-kv-results.md) | 189/192, 1.0 up to 24x |
| KV 9B + clm (+ seeds 44/45) | [`m2-kv-9b-results.md`](../notes/m2-kv-9b-results.md) | mean 0.53, 0 at 24x on 4/4 seeds (residue build-up) |
| LogTriage 4B / 9B + clm | [`m2b-logtriage-results.md`](../notes/m2b-logtriage-results.md), [`m2b-logtriage-9b-results.md`](../notes/m2b-logtriage-9b-results.md) | 4B 0.87, 9B 0.31 |
| Needle 4B / 9B + clm | [`m2c-needle-results.md`](../notes/m2c-needle-results.md), [`m2c-needle-9b-results.md`](../notes/m2c-needle-9b-results.md) | 4B 0.51 (wrong anchor deletes needles), 9B 0.72 |
| BCP smoke + variants | [`bcp-smoke-results.md`](../notes/bcp-smoke-results.md) | as configured 0/5; our method text in the instruction (v3) 2/5 |
| BCP 50 q, 4B, v3 | [`bcp50-v3-results.md`](../notes/bcp50-v3-results.md) | 10/50 (9/19 when it edited, 1/31 when not) |
| BCP 50 q, 9B, v3 | `bcp50-v3-9b-results.md` (pending) | running at handoff |

Key finding: **4B and 9B have complementary CLM failures.** The 4B executes literal recipes
(KV, LogTriage) for hundreds of turns but garbles intricate ones (Needle anchor, Sudoku
in-place edit). The 9B copies intricate recipes correctly but improvises on long literal
ones (dumps, mirror greps, chat-text answers, residue) and hits the budget wall.

Decisions tonight (logged): Sudoku skipped (seed-42 slip reproduced); no BCP judge
(substring grader, all 10 4B "correct" hand-checked as exact gold matches); `CB_SETTINGS=paper`
for every ContextBench run; BCP v3 method text is our deviation from the paper.

## Next steps (in order; also in the checklist)

1. When the 9B BCP run ends (`runs/logs/queue-bcp50-v3-9b.log` has `QUEUE DONE`):
   `python infra/bcp/report.py --out .agent/notes/figs/bcp50-v3-9b --title ... runs/bcp50-v3-9b`,
   write `bcp50-v3-9b-results.md` (compare with the 4B run), commit.
2. Swap to 4B (kill the vLLM python pid; see gotchas), run C2: KV R1000/R4000/R16000 ×
   seeds 44/45 with 4B + clm (`runs/queues/` pattern, `infra/run_queue.sh`), then update
   `m2-kv-9b-results.md` with 4 seeds per level for both models, commit.
3. `git push origin reimplementation-m1` (user asked to push once done).
4. Open questions for the user: run the BCP judge (needs 27B + ~20 GB disk)? Full 4B/9B
   no-skill ladders (cheap, mostly 0)? More seeds for Needle / LogTriage?

## Host (RunPod container)

- 1x A40 46 GB, 96 cores, 503 GB RAM. No Docker, no CAP_SYS_ADMIN.
- `/workspace` = persistent quota-limited volume (~28 GB used of ~54). `/` = container disk,
  50 GB, ~9 GB free during runs (each live trial sandbox is ~124 MB in `/root/chroots/`,
  removed when the trial ends), lost if the pod is re-created.
- Large things on `/`: venvs `/root/envs/{vllm-env,clm-env}` (clm-env now also has
  matplotlib), HF cache `/root/hf_cache` (4B + 9B), rootfs `/root/rootfs/py312slim`,
  BCP index `/root/bcp_index/`. Rebuild recipe if the pod is re-created: see git history
  of this file (e4a2438).

## Running at handoff

- vLLM **9B** on :8000 (`runs/logs/vllm-serve-9b.log`); BM25 search server on :8100
  (`runs/logs/bcp-search.log`); `infra/util_log.sh` writing `runs/logs/util-bcp-smoke-m2.csv`
  every 30 s (GPU util, memory, power, CPU busy, load, RAM).
- 9B BCP 50-question run (10 concurrent), `runs/bcp50-v3-9b/`.

## Tools added tonight

| Path | What |
|---|---|
| `infra/run_queue.sh` | run a queue file (`MODEL SKILL TASK RUN_DIR` per line) with N concurrent, `CB_SETTINGS=paper` |
| `infra/cb_report.py` | per-trial table + reward-vs-pressure plot (`--bars` for single-level grids) |
| `infra/util_log.sh` | GPU/CPU CSV logger |
| `infra/bcp/report.py` | BCP per-question table + outcome plot |
| `infra/bcp/skill/bcp_search_{clm,ids}/`, `infra/bcp/make_v3_tasks.py` | BCP method-text variants (v2 / v3) |
| `infra/run_cb_trial.sh` | `CB_SETTINGS=paper` (PAPER_KWARGS as-is) vs default `appf` (M1 overrides) |
| `infra/run_bcp_trial.sh` | `MODEL`, `BCP_SKILL`, `BCP_TASKS` switches |

Data added (gitignored): `data/cb_tasks/` now has LogTriage + Needle (all levels, seeds 42/43)
and KV seeds 44/45; `data/bcp_tasks/` all 50; `data/bcp_tasks_v3/` the v3 copies.

## Gotchas

- Kill vLLM by its pid from `pgrep -f "envs/vllm-env/bin/python.*vllm serve"`, but never in
  the same shell command that contains that pattern: `pgrep -f` then matches the shell itself
  and `kill` takes the shell down (happened tonight; harmless, server was already dead).
- Two concurrent trials of the same task used to share one sandbox root (fixed: random suffix).
- Harbor/litellm logs print "Provider List" noise for the cost lookup; ignore.
- Every proot command prints a harmless "can't chdir" warning (host cwd absent in the guest).
- The `docs(agent)` notes quote only the last edit command per trial (earlier ones are
  edited out of the trajectory by the model itself).
