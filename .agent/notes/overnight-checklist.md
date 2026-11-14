# Overnight checklist (2026-11-14 → 15)

User request (18:45 UTC): run as many ContextBench evals as possible, and BCP only if it works.
After every eval run: write results + analysis + plot to `.agent/notes/`, then commit.
Smoke 4B / 9B × skill none / clm on all 4 families. Skip Sudoku if it is still a problem
(log the decision). Watch disk.

Settings for every ContextBench run: `CB_SETTINGS=paper` (PAPER_KWARGS: budget 32768 /
reserve 2048, no step cap, no nudges, T=0.7), seeds 42 (smoke) or 42+43 (full), proot sandbox,
timeout 28800 s. One GPU: one model is served at a time, so 4B work runs first, then 9B.

Levels (closest paper.yaml rungs to 0.5x / 2x / 8x / 24x):
KV R260 / R1000 / R4000 / R16000 · LogTriage L320 / L1600 / L6400 / L12800 (max 15.8x) ·
Needle K4-C4 / K4-C24 / K8-C60 / K2-C192 · Sudoku t8 / t30 / t60 / t150.

## Phase 0: done before bed
- [x] BCP smoke, as configured: 0/5 answered → [bcp-smoke-results.md](bcp-smoke-results.md)
- [x] M2 KV 4B + clm, R260 / R1000 / R4000 (R16000 still running) → [m2-kv-results.md](m2-kv-results.md)
- [x] LogTriage + Needle tasks packaged (seeds 42/43, all levels) into `data/cb_tasks/`

## Phase A: 4B served
- [x] A0 M2 KV done: 7/8 trials 24/24, 189/192 GETs, flat ~14k context to 24x → [m2-kv-results.md](m2-kv-results.md) (committed)
- [x] A1 smoke 4B (seed 42, lowest level) × {none, clm} × {KV R260, LogTriage L320, Needle K4-C4, Sudoku t8},
      plus Sudoku t8 seed 43 + clm → [smoke-grid-results.md](smoke-grid-results.md) (committed)
- [x] A2 Sudoku: seed 42 dropped one move again (0/8, 255/256 cells), seed 43 8/8 → **skipped**, logged in decisions.md
- [x] A3 LogTriage 4B + clm: 1.0 on 7/8 up to 16x; L12800 s42 drifted after 166 turns → 0 → [m2b-logtriage-results.md](m2b-logtriage-results.md) (committed)
- [x] A4 Needle 4B + clm: mean 0.51 (1.0 at 0.5x; 0.03–0.85 above, decided by which anchor the 4B copies) → [m2c-needle-results.md](m2c-needle-results.md) (committed)
- [x] ~~A5 full 4B + clm Sudoku~~ skipped (A2)
- [x] A6 BCP variant smoke: v1 (as configured) 0/5, v2 (method in system prompt) 1/5,
      v3 (method in instruction) 2/5 correct → bar (≥ 2/5 answered) met → [bcp-smoke-results.md](bcp-smoke-results.md)
- [x] A7 BCP 50 questions with v3: **10/50 correct** (9/19 when the model edited, 1/31 when not) → [bcp50-v3-results.md](bcp50-v3-results.md) (committed)

## Phase B: swap to 9B (after all 4B trials finish)
- [x] B1 4B server stopped, 9B up 19:53 UTC
- [x] B2 smoke 9B: clm 1.0 on KV / LogTriage / Needle; none 0.71 / 0.08 / 1.0 → [smoke-grid-results.md](smoke-grid-results.md) (committed)
- [x] B3a KV 9B + clm: mean 0.53 vs 4B 0.98; budget wall in 5/6 trials above 0.5x (residue build-up) → [m2-kv-9b-results.md](m2-kv-9b-results.md) (committed)
- [x] B3b Needle 9B + clm: mean 0.72 vs 4B 0.51; 9B keeps every needle until the wall → [m2c-needle-9b-results.md](m2c-needle-9b-results.md) (committed)
- [x] B3c LogTriage 9B + clm: mean 0.31 vs 4B 0.87; walls, dumps, chat-text answers, dropped offloads → [m2b-logtriage-9b-results.md](m2b-logtriage-9b-results.md) (committed)
- [ ] B4 extra seeds 44/45, KV R1000 / R4000 / R16000, 9B + clm (6, since 20:34): is 9B < 4B on KV robust?

- [x] B5 BCP 50 q v3 on 9B: 12/50 strict, 13 after hand check (4B: 10) → [bcp50-v3-9b-results.md](bcp50-v3-9b-results.md) (committed)

## Phase C: back to 4B (after all 9B trials finish)
- [x] C1 server back to 4B (22:26 UTC)
- [ ] C2 same extra seeds 44/45 KV for 4B + clm (6) → update m2-kv-9b-results.md with 4 seeds per level, plot, commit

## Throughout
- [ ] GPU/CPU log `runs/logs/util-*.csv`; add a utilization summary to every write-up
- [ ] Disk: `/` free > 5 GB, `/workspace` < 45 GB (quota ~54 GB). Never delete weights or caches.
- [ ] Commit only notes, plots and infra scripts (`runs/`, `data/` are gitignored)
- [ ] Update the handoff file at the end
- [ ] When everything is done: `git push origin reimplementation-m1` (user request, 19:30 UTC)
