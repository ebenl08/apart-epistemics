# Handoff (temporary): CLM reimplementation, overnight runs (M2 KV/LogTriage/Needle, BCP)

Session: reimplementation. Updated: 2026-11-15 01:35 UTC (overnight runs finished and pushed; host idle, waiting on user).
Plan: [`../instruction-reimplementation.md`](../instruction-reimplementation.md).
Decisions: [`../decisions.md`](../decisions.md). Overnight checklist (live status):
[`../notes/overnight-checklist.md`](../notes/overnight-checklist.md).

## Start here (next session)

1. Read this file, then [`../notes/overnight-checklist.md`](../notes/overnight-checklist.md) (all ticked)
   and the result notes linked below.
2. No trials are running; servers and pod state are in `server-handoff.md` (local only).
3. Before launching anything, get the user's answers to the open questions in "Next steps"
   (judge, more seeds, elicitation target). The judge needs disk, and freeing it means deleting
   things, so it needs the user's OK.

## Where things stand

User's overnight brief (18:45 UTC): run as many ContextBench evals as possible, BCP if it works,
smoke 4B/9B × skill none/clm, skip Sudoku if still problematic, write results + analysis +
plot after every run and commit, watch disk, push when done.

All results in one file: [`m2-bcp-results.md`](../notes/m2-bcp-results.md). The per-run notes
below are archived in `.agent/notes/archive/`; plots and per-trial tables in `.agent/notes/figs/`.

| Run | Note | Headline |
|---|---|---|
| Smoke grid 4B + 9B × none/clm | [`smoke-grid-results.md`](../notes/archive/smoke-grid-results.md) | no-skill hits the wall on KV/LogTriage at 0.5x; 9B+clm 1.0 on all three |
| KV 4B + clm | [`m2-kv-results.md`](../notes/archive/m2-kv-results.md) | seeds 42/43: 189/192, 1.0 up to 24x; seeds 44/45: R4000 0/0 (residue wall) |
| KV 4B vs 9B, 4 seeds at R1000+ | [`m2-kv-9b-results.md`](../notes/archive/m2-kv-9b-results.md) | R1000 1.00 vs 0.74, R4000 0.50 vs 0.56, R16000 1.00 vs 0.00; budget wall 2/12 vs 8/12 |
| LogTriage 4B / 9B + clm | [`m2b-logtriage-results.md`](../notes/archive/m2b-logtriage-results.md), [`m2b-logtriage-9b-results.md`](../notes/archive/m2b-logtriage-9b-results.md) | 4B 0.87, 9B 0.31 |
| Needle 4B / 9B + clm | [`m2c-needle-results.md`](../notes/archive/m2c-needle-results.md), [`m2c-needle-9b-results.md`](../notes/archive/m2c-needle-9b-results.md) | 4B 0.51 (wrong anchor deletes needles), 9B 0.72 |
| BCP smoke + variants | [`bcp-smoke-results.md`](../notes/archive/bcp-smoke-results.md) | as configured 0/5; our method text in the instruction (v3) 2/5 |
| BCP 50 q, 4B, v3 | [`bcp50-v3-results.md`](../notes/archive/bcp50-v3-results.md) | 10/50 (9/19 when it edited, 1/31 when not) |
| BCP 50 q, 9B, v3 | [`bcp50-v3-9b-results.md`](../notes/archive/bcp50-v3-9b-results.md) | 12/50 strict, 13 after hand check; edits in 70% of trials |

Key finding: **4B and 9B have complementary CLM failures.** The 4B executes literal recipes
(KV, LogTriage) for hundreds of turns more often than not, but garbles intricate ones (Needle
anchor, Sudoku in-place edit). The 9B copies intricate recipes correctly but improvises on
long literal ones (dumps, mirror greps, chat-text answers) and lets residue build up until the
budget wall. Residue build-up hits both models (KV above 0.5x: 4B 2/12, 9B 8/12), and 2 seeds
were not enough to see that for the 4B. On BCP the 9B is slightly ahead (13 vs 10 / 50).

Decisions tonight (logged): Sudoku skipped (seed-42 slip reproduced); no BCP judge
(substring grader, all 10 4B "correct" hand-checked as exact gold matches); `CB_SETTINGS=paper`
for every ContextBench run; BCP v3 method text is our deviation from the paper.

## Next steps

All overnight items are done, committed and pushed (`reimplementation-m1`). Open questions
for the user:
1. Run the BCP judge (Qwen3.5-27B-GPTQ-Int4; needs a GPU swap and ~20 GB on `/`, which has
   ~9 GB free: freeing the 9B weights or the uv cache needs the user's OK)? It would mainly
   settle near-misses like 9B 1252 (equivalent date) and 987 (possible alias).
2. More seeds: the 4B R4000 seeds 44/45 failures show n=2 is too small; LogTriage / Needle
   4B-vs-9B gaps also rest on 2 seeds.
3. The residue failure (the `prev` cut stops being applied) is the common failure across
   models and families; a natural target for the elicitation / interp experiments.
4. Full no-skill ladders (cheap, expected ~0 above 0.5x) if a baseline curve is wanted.

## Host and running processes

Pod-specific facts (paths, caches, disk, running servers, model swap, rebuild steps) are in
`server-handoff.md` next to this file. It is local only (in `.git/info/exclude`) because the
pod and its hardware may change. If it is missing, check the pod directly (`nvidia-smi`,
`df -h`, `ps`) and the git history of this file (e4a2438) for the rebuild recipe.

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
- Failure diagnoses in the notes rest on the last edit command per trial only: the model's
  own edits remove earlier commands from the trajectory.
- n=2 seeds can hide failures (KV R4000 4B: seeds 42/43 perfect, 44/45 both 0). Treat any
  2-seed result as provisional.
