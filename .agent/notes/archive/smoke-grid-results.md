# Smoke grid: model × skill on all four ContextBench families

Date: 2026-11-14. 4B part: 18:46–19:22 UTC. 9B part: 19:54–20:15 UTC. Status: **done**.
Raw trials: `runs/smoke-{4b,9b}-{none,clm}/trials/` (gitignored).
Per-trial table (both models): [`figs/smoke-grid.md`](../figs/smoke-grid.md).

![Smoke grid, 4B and 9B](../figs/smoke-grid.png)

## Setup (control unless marked)

- Serving: vLLM 0.33.0, BF16, one shared server. Sandbox: proot.
- Agent: `ClmStream`, `CB_SETTINGS=paper` (budget 32768 / reserve 2048, no step cap,
  no nudges, T=0.7, max_tokens 8192, thinking on).
- Level: the lowest main rung near 0.5x of each family (everything fits if no tokens are
  wasted): KV R260, LogTriage L320, Needle K4-C4, Sudoku t8. Seed 42 (+ Sudoku seed 43 with clm).
- **Vary:** `skill` none / clm; model 4B (now), 9B (Phase B).
- Differs from M1: M1 used the App. F settings (32000 / 4096 / 240 steps).

## Results: Qwen3.5-4B

| Family | skill=none | skill=clm | none: how it ended | clm: edits |
|---|---|---|---|---|
| KV R260 | 0.125 (3/24 answered) | **0.958** | budget wall at op 7/27 | 3 |
| LogTriage L320 | 0.000 | **1.000** | budget wall at op 17/47 | 23 |
| Needle K4-C4 | **1.000** | 0.250 | finished (fits in context) | 4 (needles deleted) |
| Sudoku t8 | 0.875 | 0.000 (s42) / 1.000 (s43) | finished, one bad version | 8 / 7 |

## Analysis

1. **Where the stream does not fit as delivered, the skill decides everything.** KV and
   LogTriage without the skill hit the budget wall early (op 7/27, 17/47) even at ~0.5x
   pressure: the model keeps raw batches plus its own retyped copies in context. With the
   skill both score ~1.0, and LogTriage makes one offload edit per batch (23).
2. **Where everything fits, the skill can hurt.** Needle K4-C4 and Sudoku t8 fit in the
   window without edits, so `none` scores 1.0 / 0.875. With the skill the 4B must copy a
   more intricate recipe, and one slip is fatal: on Needle it dropped the `t[k:i]` slice
   that keeps the chunk's needles, so each edit deleted the needles (4/16 kept); on Sudoku
   seed 42 it lost one move in the in-place sketchpad (0/8, 255/256 cells right).
3. **Recipe complexity predicts 4B reliability.** KV / LogTriage recipes are "cut block,
   save to disk"; the Needle recipe must cut the filler but keep the lines around it, and
   Sudoku edits a board in place. The 4B executes the first kind every time and the
   second kind inconsistently (see the full Needle run, [`m2c-needle-results.md`](m2c-needle-results.md)).
4. Consequence: at higher pressure only the skill can work (nothing fits), so the full
   runs use `skill=clm`; Needle's score there measures recipe fidelity more than memory.

## Results: Qwen3.5-9B (Sudoku not run: skipped this sprint)

| Family | skill=none | skill=clm | none: how it ended | clm: edits |
|---|---|---|---|---|
| KV R260 | 0.708 (17/24) | **1.000** | budget wall at op 21/27 | 3 |
| LogTriage L320 | 0.083 | **1.000** | budget wall at op 27/47 | 23 |
| Needle K4-C4 | **1.000** | **1.000** | budget wall after the last chunk (all needles kept) | 4 |

## 4B vs 9B

1. **With the skill, the 9B is perfect on all three families**; the 4B is near-perfect on KV /
   LogTriage but garbles the Needle recipe (0.25). The 9B copied the Needle recipe
   correctly (header anchor kept), which is exactly the 4B's failure point.
2. **Without the skill, the 9B lasts longer but still hits the wall** on KV (op 21 vs 4B's 7)
   and LogTriage (op 27 vs 17). It made 0–1 edits: neither model manages context unaided.
   9B KV `none` scored 0 in M1 (App. F settings, 32000 / 4096); here 0.71 with paper settings
   (32768 / 2048), so the extra ~2.5k tokens of headroom matter at this level.
3. **So the skill, not the model size, is what makes CLM work**, and the 9B's advantage is
   recipe fidelity on the harder recipe. Full 9B + clm runs on all three families are under
   way to see whether that holds under pressure.
