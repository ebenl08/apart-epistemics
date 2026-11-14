# M1 smoke test results (ContextBench)

Date: 2026-11-14. Plan: [`../instruction-reimplementation.md`](../instruction-reimplementation.md) (M1).
Raw trials: `runs/m1/`, `runs/m1b-4b-clm/`, `runs/m1b-9b-none/` (gitignored, local only).

## Setup (control unless marked)

- Serving: vLLM 0.33.0, BF16, `--max-model-len 65536 --language-model-only`, parsers
  `qwen3_coder` / `qwen3`, prefix caching on. One A40, one model served at a time.
- Agent: `clm_contextbench:ClmStream`, `PAPER_KWARGS` plus overrides
  `context_budget_tokens=32000`, `context_budget_reserve_tokens=4096`, `max_steps=240`.
  No nudges, `ctx_hint=default`, `allow_edit_growth=fit`, T=0.7, top_p=0.95,
  `max_tokens=8192`, thinking on.
- Tasks: KV Store `R260` (pressure 0.46) and Sudoku `t8` (0.53), seed 42. These are the
  plan's 0.5x control levels; everything fits the budget if no tokens are wasted.
- Sandbox: chroot of `python:3.12-slim` (`infra/chroot_env.py`), no Docker on this host.
- **Vary:** model (Qwen3.5-4B / Qwen3.5-9B) and `skill` (`none` / `clm`).

`skill=none`: harness system prompt only (explains the mirror file
`/tmp/.live_ctx/LIVE_CTX_MAIN.txt`). `skill=clm`: plus the paper's per-family method text
(`data/ContextBench/clm_exp/skills/clm/<family>.md`, sha-checked), a concrete offload recipe.

## Results (n = 1 per cell)

| Arm | KV R260 | Sudoku t8 | Edits (KV / Sudoku) | Peak ctx (KV / Sudoku) | Gen tokens / call |
|---|---|---|---|---|---|
| 4B + `none` | 0/24, `budget_wall` at op 3/27 | 7/8 | 0 / 0 | 25.6k / 29.8k | 2533 / 1961 |
| 4B + `clm` | **22/24**, 27/27 ops | 0/8 | 3 / 8 | 11.2k / 9.5k | 271 / 515 |
| 9B + `none` | 0/24, `budget_wall` at op 2/27 | 6/8, `budget_wall` at op 7/8 | 0 / 0 | 34.8k / 29.8k | 1564 / 2191 |

## Findings

1. **Without the skill, neither model edits its context** (0 real edits in all four
   `none` trials). On KV both die at the budget wall in 2-3 ops: 4B writes each batch to
   a file with a heredoc, which retypes the batch, so every batch sits in context twice
   (~10k tokens). 9B spends its calls trying to read the batch from stdin. Model size
   (4B to 9B) does not help.
2. **4B + `clm` performs CLM**: one offload edit per KV batch, flat context (~4k), 22/24.
   For reference, the paper's Qwen3.6-27B CLM rows score 1.0 at KV R1000 and Sudoku t150
   (`data/ContextBench/docs/HARBOR_SMOKE.md`, "Comparison with the paper's Qwen3.6 rows").
3. **4B + `clm` Sudoku 0/8 is one dropped move.** Move v1 (r1c1 = 9) was never applied to
   the in-context sketchpad; all later moves were. Final board 255/256 cells correct
   (`reward_final_cell` 0.996), but exact-match grading zeroes every version after the
   slip. The `clm` Sudoku method edits one sketchpad in place, so early errors propagate;
   without the skill the model reprints boards and an error costs one version.
4. **Cost**: with the skill, calls generate 5-8x fewer tokens; M2/M3 will run well under
   the plan's time estimates.
5. **Paper reference correction**: the plan compared `skill=none` to App. F (Qwen3.6-27B,
   KV 22.3%, Sudoku 45.3%). Those are the no-skill starting point of the in-context
   skill-evolution experiment, on a dev split. The paper's reported CLM condition is
   `skill=clm` (all Fig. 2 CLM rows, `clm_exp/skills/README.md`).

## Confound

The 9B KV trial had 2 commands fail because the chroot had no `/dev/fd` or `/dev/stdin`
(no `/proc`, mounts not permitted). The model was already off track (the data is not on
stdin), so the 0 likely stands. The 4B trials never touched these paths. Fixed afterwards
by switching the sandbox to proot with host `/proc`, `/dev`, `/sys` bound.

## Status

Pipeline verified end to end (sandbox, serving, parsers, snapshots, verifier).
Go for Qwen3.5-4B with `skill=clm`. Next: BCP smoke test with 4B, then M2/M3.
