# Handoff: M6 H3 (causality) — directional ablation of the SE direction: what works, what does not, what next

Date: 2026-11-16 (times UTC+8). Companion to [`handoff-m6-paper.md`](handoff-m6-paper.md) (H1/H2, paper).
All changes and bugs with reasons: [`../decisions.md`](../decisions.md) (entries from ~11:55 onward).
Next-step plan awaiting approval: [`../instruction-h3-clean.md`](../instruction-h3-clean.md).

## Question

H3: does intervening on the residual-stream direction that encodes semantic entropy (SE) change the model's
context-decision uncertainty (decision level), and eventually task reward (task level, not started)?

## Method (works; reuse it)

- **Direction:** diff-of-means (DoM) of TBG activations at layer 20 (9B), SE > 0 minus SE = 0
  (`runs/m6-probe/direction-m5-9b.npz`, key `diff_of_means`). Chosen over the probe weight because mass-mean
  directions tend to be more causal (Marks & Tegmark 2023); cos(probe w, DoM) = 0.09.
- **Intervention = weight orthogonalization** (Arditi et al. 2024): every matrix writing to the residual stream
  (embed_tokens, `linear_attn.out_proj`, `self_attn.o_proj`, `mlp.down_proj`; 65 matrices) gets
  W ← (I + (λ − 1) d dᵀ) W. λ = 0 ablates, 0 < λ < 1 dampens, λ > 1 amplifies. The result is a plain checkpoint, so
  **vLLM serves it at full speed** (additive steering would need HF generation, too slow here without
  `causal_conv1d`). `ablate.py make|check`; deterministic, ~1 min.
- **Projection check works:** after editing, |h·d|/|h| ≤ 0.0006 at every layer (before: 0.07–0.16 for DoM).
- **Measurement reuses the M6 pipeline unchanged:** same decision points, replay and points copied from
  `runs/m6-se`, same per-point seeds for the first 10 samples, same labeller; outputs `runs/m6-h3/<cond>/`.
  `h3_analyze.py` pairs each point with the 9B baseline and reports SE three ways:
  plain (first 10 samples), valid-only (= decision-only: `ok` samples only), rejection-sampled (first 10 samples with
  a valid tool call; failed commands kept). `H3_QUEUE=runs/m6-se/queue-h3sub.txt` restricts to the 16-trial subset.

## Conditions run and results

Subset = 2 trials per family × level (`queue-h3sub.txt`, 547 points): KV R260 s44–45, R1000 s46–47, R4000 s46–47,
R16000 s46–47; LogTriage L320 s44–45, L1600 s44–45, L6400 s48–49, L12800 s44–45.

| condition | trials | format failures | agree w/ logged | ΔSE plain (p) | ΔSE decision-only (p) | per trial, decision-only [95% CI] |
|---|---|---|---|---|---|---|
| `rand` (random dir, λ = 0) | 42 (all) | 0.2% | 91% | −0.009 (0.55) | −0.007 (0.56) | −0.006 [−0.015, +0.003] |
| `dom05` (DoM, λ = 0.5) | 16 | **0.1%** | 90% | **−0.048 (0.004)** | **−0.062 (0.0001)** | **−0.053 [−0.090, −0.021]** |
| `dom` (DoM, λ = 0) | 16 | **~48%** | 25% | +0.72 (1e-52) | +0.17 (1e-8) | +0.16 [+0.12, +0.20] |
| `dom-rs` (λ = 0, rejection-sampled, stopped early) | 9 (289 pts) | 48% of first 10 | 27% | +0.71 (1e-34) | **+0.28** (rs, n = 243) | rejection-sampled SE incl. failed commands: +0.60 [+0.46, +0.72] |

Baseline (same 547 points): SE 0.242, decision-only 0.171, agreement with logged decision 89.5%.

- **λ = 0.5, by family:** LogTriage SE falls at every level (L320 −0.05, L1600 −0.16, L6400 −0.10, L12800 −0.10);
  KV rises slightly at every level (+0.01 to +0.04).
- **λ = 0:** 44–48% of samples lose the tool-call format (40% plain text, 29% fenced bash block, 20% empty answer,
  11% hit the 8192-token cap); worse at higher pressure (KV R1000 24%, R16000 53%, LT L6400 70%). SE splits into
  0.60 bits from format failure + 0.31 within groups (baseline 0.008 + 0.197).
- **Rejection sampling at λ = 0** (first trials): every point reached 10 valid calls (~16 samples drawn); among valid
  calls 16% of commands fail. Decision-only SE also rises (plug-in SE is biased low with fewer samples; rejection
  sampling gives 8.4 ok samples per point vs 6.6 plain and ~9.7 baseline, so it is the fairer comparison).
  Final (9 trials, stopped by the user's rule at 8+): 23 samples drawn per point on average, 84% of points reached
  10 valid calls (16% hit the 40-sample cap); 18% of valid calls fail; decision-only SE 0.145 → 0.290 (plain) →
  **0.423 (rejection-sampled)**. Table: `../notes/figs/h3-sub-final.md`.

## What works

1. The weight-orthogonalization + vLLM + replay pipeline: fast, deterministic, measurable end to end.
2. Pairing by point and seed against the baseline, with three SE variants, cleanly separates "broken format",
   "failed commands" and "different context decision".
3. **λ = 0.5 is a clean dose:** format intact (0.1% failures), and decision uncertainty drops (p = 0.0001), driven by
   LogTriage. This is the best causal evidence so far.
4. `rand` (all 42 trials) is flat under every SE variant.

## What does not work (or is not interpretable yet)

1. **The DoM direction is confounded** (9B, 1409 points, layer 20): cos(DoM, context-fill direction) = +0.45; 31% of
   its squared norm lies in span(fill, family, turn type); 36% of SE > 0 points involve a failed-command cluster;
   cos(DoM, DoM of decision-only SE > 0) = 0.33. So the λ = 0.5 effect could be context length or command success.
2. **λ = 0 is off-distribution:** ablating the direction collapses tool-call formatting; "uncertainty rises when the
   model breaks" is weak evidence. Rejection sampling fixes the measurement but not the interpretation.
3. **`rand` is a weak control:** activations spread 0.28 along a random direction vs 7.06 along DoM (25× less), so it
   controls for "editing weights", not for "removing a large direction".
4. **The probe-weight direction is not usable for ablation:** spread along it is 0.30 (≈ random), so projecting it out
   removes almost nothing. It would only matter with additive steering (not possible via weight edits; HF is slow).
5. **Non-monotonic dose:** λ = 0.5 lowers SE, λ = 0 raises it (with format collapse). No λ > 1 point yet.
6. **Family-specific effect:** KV moves the other way at λ = 0.5; 2 trials per cell cannot say why.
7. **Task-level H3 (reward under intervention) not started.**

## What needs to be done (in order)

1. **Approve and run [`instruction-h3-clean.md`](../instruction-h3-clean.md)** (~1.3 h wall, ~2.5 GPU-h, ~$1.50):
   - `se_clean`: DoM on **decision-only SE** with activations residualized on fill, fill², turn index,
     family × level, turn type; sanity gate: held-out AUROC of the projection > 0.6.
   - `fill_ctl`: context-fill DoM orthogonalized to `se_clean` (a large, matched control).
   - Both at λ = 0.5 on the 16-trial subset; primary readout = paired Δ decision-only SE; decision table fixed in
     the plan.
2. If `se_clean` moves decision-only SE and `fill_ctl` does not: add **λ = 1.5** (amplify; SE should rise) for a
   three-point dose curve without the broken λ = 0.
3. Then the **task-level test:** full ContextBench trials with the λ = 0.5 (and 1.5) model vs the M5 baseline reward,
   same seeds; needs the M5 trial runner (`infra/run_queue.sh`) with the edited weights served.
4. Repeat on 9B-RL (direction at layer 28, `direction-m5-9b-rl.npz`) if the 9B result holds.
5. Fold decision-only SE into `analyze.py` / `probe.py`; regenerate H1/H2 tables from code.

## Code (all in `infra/semantic_entropy/`)

| file | role |
|---|---|
| `ablate.py` | `make <src> <direction.npz|random:SEED> <lam> <out>`; `check <model> <direction.npy>`; self-test |
| `h3_chain.sh` | full-queue conditions (`dom`, `rand`): edit → check → serve → `m6_run.sh` → analysis |
| `h3_sub.sh` | 16-trial subset, plain stage (its rejection stage is broken: `m6env.sh` overwrites `$R`; use `h3_rs.sh`) |
| `h3_rs.sh`, `h3_rs_rev.sh` | rejection sampling (forward worker; reverse worker with mkdir claims, for a second pod) |
| `collect.py topup` | top up a trial to 10 valid tool calls per point (cap 40, new seeds); then re-`execute` |
| `m6_rev.sh` | reverse-order second sampler (skips complete trials, stops at in-progress one) |
| `h3_analyze.py` | paired analysis, plain / decision-only / rejection-sampled SE, `H3_QUEUE` filter |

## Infra lessons (cost time today)

- First vLLM start on a fresh pod can die silently during the flashinfer JIT build; the scripts retry once.
- `hf download` prints `  path: <dir>`; use `snapshot_download` to get the path.
- `pkill -f <pattern>` over SSH can kill its own shell when the pattern is in the command line; use small scripts
  and kill by session id (`ps -o sid=`; guard against an empty sid).
- `m6env.sh` sets `R` and `cd`s into the repo; do not use `R` as a variable in scripts that source it.
- Ablated models (λ = 0) produce runaway 8192-token generations; one-trial-at-a-time sampling then idles the GPU.
  Run a second sampler / several trials in parallel and watch KV-cache use, not GPU %.
- The local network dropped twice (rsync, watcher). A watcher must treat an SSH failure as "unknown", not 0.
- Pods: `i2qg43j6zshuor` (pod 1), `rckduvamr1vclf` (pod 2), 1×A40 $0.59/h each, volume `hri0q37of4`.
  Old 9B pod `obvrywyztadwv4` is stopped (could not restart: no GPU on its host). Pod 2 stopped 2026-11-16 ~18:30;
  pod 1 stopped after the `runs/` copy to the laptop finished. Both keep their container disks while stopped
  (edited weights deleted; base 9B weights in `/root/hf_cache`), but a restart can fail if the host has no free GPU —
  then create a new pod on the same volume (`setup_pod.sh`, `m6env.sh`).
