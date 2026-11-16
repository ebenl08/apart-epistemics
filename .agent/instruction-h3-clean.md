# Plan: H3 with a cleaned SE direction and a context-fill control (draft for user review)

Date: 2026-11-16. Follows the H3 decision-level runs (`dom` λ = 0, `dom05` λ = 0.5, `rand`) on the 16-trial subset
(`runs/m6-se/queue-h3sub.txt`, 547 decision points). Decisions so far: `decisions.md`.

## Why

The current SE direction (`dom`: diff-of-means of layer-20 TBG activations, SE > 0 vs SE = 0) is contaminated:

| check (9B, 1409 points) | value |
|---|---|
| SE > 0 points whose SE involves a failed bash command (`invalid`) | 36% |
| cos(DoM, DoM of decision-only SE > 0) | 0.33 |
| cos(DoM, context-fill direction) | +0.45 |
| share of DoM's squared norm in span(fill, family, turn type) | 0.31 |
| spread of activations along DoM / random / probe weight (std of projection) | 7.06 / 0.28 / 0.30 |

So the λ = 0.5 drop in SE could come from removing context-length information or command-success information rather
than context-decision uncertainty. The probe weight direction is not a usable alternative for ablation: activations
barely vary along it (0.30, same as random), so projecting it out changes almost nothing.

## Question

Does removing a direction that encodes **context-decision uncertainty only** (not context length, not command success)
change the model's decision uncertainty, and is the effect absent when an equally large **context-length** direction
is removed instead?

## Directions (CPU only, from the saved activations `runs/m6-probe/m5-9b__*.npz`)

1. **`se_clean`** (cleaned SE direction)
   - Target: **decision-only SE** = SE over samples with status `ok` only (drop `invalid`, `no_tool_call`,
     `context_status`, `error`); points with < 2 ok samples dropped. Binarized at > 0.
   - Features: TBG activations at layer 20 (same layer as `dom`, for comparability).
   - Residualize every activation dimension on covariates by OLS: fill, fill², turn index, family × level (one-hot),
     turn type. Take the diff-of-means of the residuals (decision-SE > 0 minus = 0); unit-normalize.
   - Sanity: (a) cos with `dom` and with the fill direction (should be ≈ 0 with fill by construction);
     (b) 5-fold GroupKFold-by-trial AUROC of the projection onto the direction for decision-only SE > 0
     (direction fitted on train folds) — must be > 0.6 to proceed; (c) spread of activations along it.
2. **`fill_ctl`** (context-length control)
   - Diff-of-means between top and bottom fill quartile on raw layer-20 TBG activations, then orthogonalized against
     `se_clean` so the control removes no SE component. Unit-normalized.
   - Report its spread next to `se_clean`'s; the control is meaningful because both are large directions (unlike `rand`).

## Intervention and sampling (one condition per pod, in parallel)

**Control (unchanged from `dom05`):** 9B base weights; weight orthogonalization of the 65 residual-stream writers
(`ablate.py`) at **λ = 0.5**; same 16 trials, same 547 points, same per-point seeds, K = 10, T 0.7 / top_p 0.95 /
thinking on / max_tokens 8192; same labeller and execution; served by vLLM 0.33.0 under the 9B's name.

**Vary:** the direction — `se_clean` (pod 1) vs `fill_ctl` (pod 2).

- Projection check after editing (|h·d|/|h| per layer) as before.
- Format guard: if format failures exceed 2% of samples, also run rejection sampling (`h3_rs.sh`) for that condition.

## Readouts (`h3_analyze.py`, `H3_QUEUE=queue-h3sub.txt`)

- **Primary:** paired change in **decision-only SE** (the existing "valid only" column) vs the 9B baseline:
  per point (Wilcoxon) and per trial (mean, 95% bootstrap CI over the 16 trials).
- Secondary: plain SE; `invalid` rate; format-failure rate; agreement with the logged decision; per family × level.
- Compared side by side with `dom05` (old direction, λ = 0.5) and `rand` on the same points.

**Interpretation, fixed in advance:**

| `se_clean` | `fill_ctl` | reading |
|---|---|---|
| CI excludes 0 | CI includes 0 | decision uncertainty is causally carried by the cleaned direction, beyond context length |
| CI excludes 0 | CI excludes 0, same sign | effect not specific to uncertainty; context length (or any large direction) moves SE |
| CI includes 0 | CI excludes 0 | the `dom05` effect was a context-length effect |
| CI includes 0 | CI includes 0 | no causal evidence at λ = 0.5; the `dom05` effect came from the confounded components |

Optional follow-up only if row 1: `se_clean` at λ = 1.5 (amplify) on the same subset — SE should rise.

## Code changes (small)

- `infra/semantic_entropy/h3_directions.py` (new): computes `se_clean` and `fill_ctl`, prints the sanity checks,
  saves `runs/m6-probe/direction-m5-9b-{se_clean,fill_ctl}.npy`.
- `ablate.py`: accept a `.npy` direction file (today it reads `diff_of_means` from an `.npz`).
- Runs reuse `h3_sub.sh` (plain stage) and `h3_rs.sh` (only if the format guard trips).

## Cost

A40 at $0.59/h per pod; both pods already running.

| step | where | wall-clock | GPU-hours | cost |
|---|---|---|---|---|
| compute directions + sanity checks | pod CPU (while GPUs busy) | ~0.2 h | 0 extra | $0 |
| `se_clean` λ = 0.5, 16 trials (build + serve ~0.1 h, sample ~0.7 h, execute tail ~0.2 h; `dom05` took 0.95 h) | pod 1 | ~1.0 h | 1.0 | $0.59 |
| `fill_ctl` λ = 0.5, 16 trials | pod 2 | ~1.0 h (parallel) | 1.0 | $0.59 |
| analysis + write-up | pod CPU, then stop pods | ~0.25 h | 0.5 (pods up) | $0.30 |
| **total** | | **~1.3 h after the GPUs are free** | **~2.5** | **~$1.50** |
| optional: rejection sampling if format guard trips | per condition | +1–2 h | +1–2 | +$0.6–1.2 |
| optional: `se_clean` λ = 1.5 | one pod | +1.0 h | +1.0 | +$0.59 |

**Scheduling:** both GPUs are busy with the λ = 0 rejection sampling (2/16 trials done at 17:15 UTC+8; at the
current rate the rest needs ~2 h, i.e. ~4 GPU-hours, ~$2.40). Options:
- (a) let it finish, then this plan: done ~20:30 UTC+8;
- (b) stop it after the trials in progress (~8 of 16), then this plan: done ~19:30 UTC+8;
- (c) stop it now (keep the finished trials), then this plan: done ~18:45 UTC+8.
