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
- [x] A0 M2 KV done: 7/8 trials 24/24, 189/192 GETs, flat ~14k context to 24x → m2-kv-results.md
- [ ] A1 smoke 4B (seed 42, lowest level) × {none, clm} × {KV R260, LogTriage L320, Needle K4-C4, Sudoku t8},
      plus Sudoku t8 seed 43 + clm (is the dropped move repeatable?) → `smoke-grid-results.md`
- [x] A2 Sudoku: seed 42 dropped one move again (0/8, 255/256 cells), seed 43 8/8 → **skipped**, logged in decisions.md
- [ ] A3 full 4B + clm: LogTriage 4 levels × 2 seeds (8) → `m2b-logtriage-results.md`, plot, commit
- [ ] A4 full 4B + clm: Needle 4 levels × 2 seeds (8) → `m2c-needle-results.md`, plot, commit
- [ ] A5 (only if A2 is OK) full 4B + clm Sudoku 4 levels × 2 seeds
- [ ] A6 BCP variant smoke: same 5 questions + our BCP method text (offload search results to
      notes, write a provisional answer early). Our addition, labeled as a deviation.
      ≥ 2/5 answered → run the 50-question sample with it; otherwise stop BCP.

## Phase B: swap to 9B (after all 4B trials finish)
- [ ] B1 stop the 4B server, start `infra/serve_qwen35_9b.sh`
- [ ] B2 smoke 9B (seed 42, lowest level) × {none, clm} × 4 families → add to `smoke-grid-results.md`, commit
- [ ] B3 if time: full 9B + clm on whichever families work (KV first) → notes, plot, commit

## Throughout
- [ ] GPU/CPU log `runs/logs/util-*.csv`; add a utilization summary to every write-up
- [ ] Disk: `/` free > 5 GB, `/workspace` < 45 GB (quota ~54 GB). Never delete weights or caches.
- [ ] Commit only notes, plots and infra scripts (`runs/`, `data/` are gitignored)
- [ ] Update the handoff file at the end
