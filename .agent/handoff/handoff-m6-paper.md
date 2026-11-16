# Handoff: M6 paper — semantic entropy of context decisions predicts failure and is decodable (H1, H2)

Date: 2026-11-16 (times UTC+8). For whoever writes or revises the paper. Causal work (H3) has its own handoff:
[`handoff-m6-causality.md`](handoff-m6-causality.md).

## Where things are

| what | path |
|---|---|
| Paper draft (up to date with everything below) | [`../notes/m6-se-paper.md`](../notes/m6-se-paper.md) |
| Lab notes, all numbers, milestone table | [`../notes/m6-se-results.md`](../notes/m6-se-results.md) |
| Decision log (every change, bug, and why) | [`../decisions.md`](../decisions.md) |
| Original plan (pre-registered tests and go/no-go) | [`../instruction-semantic-entropy.md`](../instruction-semantic-entropy.md) |
| Figures and full tables | `../notes/figs/` (`m6-se-m5-9b*.{md,png,csv}`, `m6-se-m5-9b-rl*`, `probe-m5-9b*.md`, `direction-*.npz`) |
| Raw data (volume `hri0q37of4`; local copy in `runs/`, gitignored) | `runs/m6-se/` (per-point results, samples), `runs/m6-probe/` (activations `.npz`), `runs/m5-lmlog/` (logged LM calls), `runs/m5-9b{,-rl}/trials/` (rewards) |
| Code | `infra/semantic_entropy/`: `entropy.py` (SE, labeller), `collect.py` (replay → sample → execute), `analyze.py` (H1), `probe.py` (H2), `m6_chain.sh` (unattended full run) |

## One-paragraph summary

We replay 42 logged ContextBench trials per model (Qwen3.5-9B and its RL checkpoint, `skill=clm`; KV store and
LogTriage at 4 pressure levels) byte-exactly, resample 10 replies at every decision point (1409 / 1435 points),
execute each sampled command in a reconstructed sandbox, and cluster samples by their effect on the context
(per-block stay / edit / offload / delete + clobber, or a status). Discrete semantic entropy (SE) over these
clusters predicts lower reward at fixed pressure in both models, and a linear probe reads it from the residual stream
before generation. Both results hold when SE is restricted to the context decision itself (excluding failed commands
and malformed tool calls).

## Headline results (all pre-registered tests passed)

**Validation (both models):** Gate A replay fidelity 40/42 (9B) and 41/42 (9B-RL) trials byte-identical (divergences
are `ls -la` metadata; later points dropped); Gate B labeller self-consistency 1397/1397 and 1421/1421; 0 sample
errors; 0 prompt-token mismatches; 10/10 hand-checked labels (9B).

**H1: partial Spearman ρ(trial mean SE, reward | family × level), 95% bootstrap CI over trials**

| SE measure | 9B (n = 42) | 9B-RL (n = 41) |
|---|---|---|
| SE (pre-registered) | **−0.587 [−0.775, −0.282]** | **−0.477 [−0.736, −0.094]** |
| max SE | −0.42 [−0.72, −0.05] | −0.355 [−0.723, +0.065] |
| decision-only SE | −0.496 [−0.731, −0.120] | −0.446 [−0.698, −0.063] |
| status-only SE (failed command / format) | −0.472 [−0.675, −0.218] | −0.287 [−0.618, +0.116] |
| OLS SE coefficient (p); ΔR² over level | −2.02 (< 0.001); +0.26 | −3.16 (0.003); +0.19 |
| OLS + mean fill + n points | −1.65 (0.0003) | −3.02 (0.006) |
| joint OLS: decision / status coefficient (p) | −1.50 (0.010) / −2.85 (0.004) | −5.59 (0.004) / +0.54 (0.82) |

**H2: probe at the last prompt token (TBG), 5-fold GroupKFold by trial**

| target | 9B | 9B-RL | context-length control (fill + turn index) |
|---|---|---|---|
| SE > 0, AUROC (layer chosen in inner folds) | **0.741** (L18–20) | **0.818** (L28) | 0.578 / 0.493 |
| SE, Spearman | 0.466 | 0.383 | 0.159 / 0.004 |
| SE > 0 at last response token (SLT) | 0.648 | 0.729 | |
| SE residualized on fill, Spearman | 0.371 | 0.238 | |
| decision-only SE > 0, AUROC (fixed layer 20 / 28) | **0.766** | **0.809** | 0.520 / 0.487 |
| decision-only SE, Spearman (fixed layer) | 0.433 | 0.347 | 0.048 / −0.006 |
| shuffled labels | 0.483 | 0.522 | |

**9B vs 9B-RL:** RL scores much higher under pressure (level 4: KV 0.50 vs 0.25, LogTriage 0.64 vs 0.25), hits the
wall less (8 vs 18 trials) and is far more certain (84–96% of points at SE = 0; mean SE falls 60–80% per cell). Its
residual uncertainty still predicts failure, with a larger per-bit coefficient.

## Decision-only SE (new, in paper §3.6, §5.7, §6.2)

- **Why:** status outcomes (`invalid` = command exited non-zero with no context change; `no_tool_call`;
  `context_status`; `error`) are clusters too, so SE mixes "which context decision" with "does the command work".
  At baseline, 36% of SE > 0 points involve a status cluster; format failures are only 0.2% of samples, so the
  status part is mostly failed commands.
- **Definitions:** decision-only SE = SE over `ok` samples (≥ 2 needed, else the point is dropped); status-only SE =
  entropy of the status variable with all `ok` merged.
- **Result:** trial mean SE and decision-only SE correlate 0.93 / 0.91. Decision-only SE reproduces H1 and H2 in both
  models. In the 9B, command-success uncertainty is a second predictor of failure (joint OLS p = 0.004) and is partly
  predictable from context length (control AUROC 0.675); in 9B-RL it adds nothing.
- **How to present:** keep the pre-registered SE as the headline (it was fixed in advance) and give decision-only SE
  as the robustness result that answers "is this just tool-use uncertainty?". Abstract already says this.
- **Reproduce:** the scripts used are in the decision log (2026-11-16 ~17:30); the computation is short (split the
  stored sample keys in `runs/m6-se/<trial>.jsonl` by status; probes at a fixed layer on `runs/m6-probe/*.npz`).
  Not yet folded into `analyze.py` / `probe.py`.

## Corrections already made (do not reintroduce)

- **"First half of trial" result is weak.** 9B: ρ −0.24; OLS p = 0.028 only when controlling for first-half fill,
  p = 0.18 with whole-trial fill. 9B-RL: no early signal (ρ −0.10). The paper calls it weak evidence.
- **Harmful-edit AUROC (0.38 / 0.35) is not evidence against H1:** the proxy marks 92–93% of edit turns harmful
  (the recipe always deletes old turns). The ground-truth label (deleted SET later queried) is not built.
- **Mean SE at fill ≥ 0.75** has wide CIs (19 / 8 trials); do not lean on it.

## Figures

- Fig 1 `figs/m6-se-m5-9b.png` (9B; your local version has error bars and is uncommitted — keep yours).
- Fig 2 `figs/m6-se-fill-m5-9b.png` (point SE vs fill; per-bin mean ± CI version still to do).
- Fig 3 `figs/m6-se-m5-9b-rl.png` (9B-RL; **no error bars** — regenerate with the same code as Fig 1).
- No figure yet for decision-only vs status-only SE; a two-panel version of Fig 1's right panel would be natural.

## Limitations to state (in paper §7)

Recipe floor (50–96% of points at SE = 0); 10 samples per point (noisy labels); n = 42 trials per model; no
step-level ground truth; one model family and one skill (`clm`); SE is total uncertainty; SE mixes decision and
command-success uncertainty (addressed by decision-only SE); results are correlational (H3 in progress).

## Open writing tasks

1. Regenerate Fig 3 with error bars; optional decision-vs-status figure.
2. Decide how much H3 to include: it is preliminary and the direction is confounded (see the causality handoff);
   safest is a short "exploratory" paragraph or future work. The paper's §8 H3 paragraph is current as of 16:00 and
   should be replaced with the summary from the causality handoff.
3. Fold decision-only SE into `analyze.py` / `probe.py` so the numbers regenerate from code.
4. References in the paper were checked (arXiv IDs resolve), including Arditi et al. 2024 and Marks & Tegmark 2023.
