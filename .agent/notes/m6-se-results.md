# M6 semantic entropy of CLM context decisions: results (9B)

Plan: [`../instruction-semantic-entropy.md`](../instruction-semantic-entropy.md). Decisions: [`../decisions.md`](../decisions.md).
Code: `infra/semantic_entropy/` (`entropy.py`, `collect.py`, `m6_run.sh`, `m6_status.sh`, `analyze.py`).
Pod `obvrywyztadwv4` (1×A40, $0.59/h, EU-SE-1). Outputs on the volume: `runs/m6-se/`, logs `runs/logs/m6-*.log`.

## Config

**Control (M5, unchanged):** M5 `skill=clm` 9B trials (42 logged: KV R260 s44–49, KV R1000/R4000/R16000 s46–49,
LogTriage 4 levels s44–49), `CB_SETTINGS=paper`, vLLM 0.33.0 BF16 prefix caching, rootfs
`sha256:05a994d2…` (same as M5), sampling T 0.7 / top_p 0.95 / thinking on / max_tokens 8192 (the logged request body, resent as is).

**New:** K = 10 samples per point (`n=10`, per-point seed), ≤ 40 points per trial (all `context_edit_turn`s +
5 `context_stay_turn`s per fill bin, capped at 40), outcome = per-block stay/edit/offload/delete + clobber flag,
or `invalid` / `no_tool_call` / `context_status` / `error`; discrete SE in bits.

## Milestones

| # | Done when | State |
|---|---|---|
| 0 | Log fields confirmed | done (earlier session) |
| 1 | `entropy.py` self-check | **done** |
| 2 | Gate A on dev trials | **done: 4/4 trials, 432/432 turns byte-identical** |
| 3 | Gate B + 10 labels hand-checked | **done: Gate B 160/160; 10/10 labels correct** |
| 4 | SE for dev trials; 5 high-SE points read | **done** (below) |
| 5 | Full 9B run + QA | **done: 42/42 trials, 1409 points, 14,090 samples, 0 errors, 0 prompt-token mismatches, Gate B 1397/1397** |
| 6 | Part 2 analysis, go/no-go | **done: GO** (partial ρ = −0.59) |
| 7 | Part 3 probe | **done: TBG probe AUROC 0.74 (controls 0.58 / 0.48), Spearman 0.47** |

## Dev trials (milestones 2–4)

| trial | reward | mean SE | max SE | share SE = 0 | edit-turn SE (n) | stay-turn SE (n) | invalid samples |
|---|---|---|---|---|---|---|---|
| KV R4000 s46 (wall) | 0.125 | 0.30 | 1.36 | 0.57 | 0.27 (27) | 0.36 (13) | 21 |
| KV R4000 s49 | 1.0 | 0.36 | 1.52 | 0.57 | 0.39 (31) | 0.26 (9) | 20 |
| LT L1600 s49 (wall) | 0.0 | 0.21 | 1.57 | 0.70 | 0.25 (23) | 0.14 (17) | 1 |
| LT L1600 s47 | 1.0 | 0.04 | 0.47 | 0.93 | 0.04 (33) | 0.00 (7) | 0 |

- Samples are diverse (10 distinct reasoning traces at every point checked), but most converge on the skill's
  offload recipe, so 57–93% of points have SE = 0 (plan risk 2, "recipe floor"). SE is not flat, though.
- **The 5 highest-SE points** (1.29–1.57 bits) all mix three kinds of decision:
  1. offload the incoming batch now (the recipe);
  2. answer or look up a pending GET first, leaving the context untouched (`grep 'SET K… =' /tmp/ctx_offload/*`);
  3. the same recipe but cutting a different set of earlier turns (e.g. deleting 6 old blocks vs editing 3 of them).
  These are real context-management choices, not labelling noise.
- LogTriage: the failed trial (s49) has 5× the mean SE of the successful one (s47). KV: no difference on this pair.
- Hand check (10 random KV R4000 s46 samples): the offload script labels the SET-BATCH block `offload` and the
  turns it cut (not saved) `delete`; a `grep` on a missing offload file is `invalid` (exit 2, no edit); an ANSWER `printf`
  leaves every block `stay`. All 10 correct.

## Full 9B run (milestone 5)

- Pass 1 on 42 trials: 40 identical, 2 diverge, both on `ls -la /tmp` (directory size / mtime differ; disk content
  the same). Per the plan, points after the divergence are dropped: LT L320 s49 keeps turns < 43 of 84, LT L1600 s45
  keeps < 101 of 130.
- 1409 points chosen. Sampling at 16 concurrent points (dev used 8; KV cache was at 4%), plus a second
  sampler walking the queue in reverse (first at 16, which caused 68 vLLM preemptions in ~10 min; restarted at 6,
  no further preemptions). Preemption recomputes, it does not change samples. Sampling 18:50–20:30 UTC (~1.7 h).
- Gate B 1237/1237 on the 38 non-dev trials (+160/160 dev). 0 sample errors, 0 prompt-token mismatches.

## Part 2: SE vs reward (H1), 9B, n = 42 trials

Full tables: [`figs/m6-se-m5-9b.md`](figs/m6-se-m5-9b.md); plots `figs/m6-se-m5-9b.png`, `figs/m6-se-fill-m5-9b.png`;
per-trial CSV `figs/m6-se-trials-m5-9b.csv`. No format-slip trials among the 42 logged ones.

| cell | n | reward | walls | mean SE | share SE = 0 |
|---|---|---|---|---|---|
| KV R260 | 6 | 0.93 | 1 | 0.07 | 0.91 |
| KV R1000 | 4 | 0.54 | 2 | 0.19 | 0.70 |
| KV R4000 | 4 | 0.53 | 2 | 0.41 | 0.50 |
| KV R16000 | 4 | 0.25 | 3 | 0.33 | 0.55 |
| LT L320 | 6 | 0.94 | 0 | 0.10 | 0.82 |
| LT L1600 | 6 | 0.40 | 3 | 0.21 | 0.71 |
| LT L6400 | 6 | 0.24 | 3 | 0.23 | 0.67 |
| LT L12800 | 6 | 0.25 | 4 | 0.14 | 0.78 |

**Main test (fixed in the plan): partial Spearman ρ(trial mean SE, reward | family×level) = −0.587,
95% bootstrap CI [−0.775, −0.282].** Strong by the plan's bar (|ρ| ≥ 0.5). Max SE: −0.42 [−0.72, −0.05].
Mean SE over points with fill ≥ 0.75: −0.31 [−0.87, +0.30] (only 19 trials have such points).

- Regression `reward ~ mean_SE + C(family:level)`: SE coefficient −2.02 (SE 0.40, p < 0.001); ΔR² = +0.26
  (0.40 → 0.66). A trial 0.1 bits more uncertain on average scores ~0.20 lower at the same pressure.
- Robustness (not pre-registered):
  - with mean fill and number of points added: coefficient −1.65, p = 0.0003;
  - KV alone ρ = −0.78 (n 18), LogTriage alone ρ = −0.51 (n 24);
  - edit turns only ρ = −0.45, stay turns only ρ = −0.42;
  - **SE from the first half of each trial only: ρ = −0.24; OLS with fill p = 0.03.** Uncertainty is present
    before the failure, not only at the wall;
  - point SE vs fill: Spearman 0.20, so SE is not mainly context length.
- SE rises with pressure up to level 3, then falls at level 4 in both families (untested guess: level-4 trials
  hit the wall early, so they have fewer points and fewer edit decisions).
- Step level:
  - harmful-edit proxy AUROC 0.38: **the proxy is uninformative**. 971 of 1051 edit turns are "harmful" by it
    because the recipe always deletes the previous command turns (routine, not damage). The plan's ground-truth
    label (a deleted SET later asked for) was not built; it is the next thing to add for a step-level claim;
  - AUROC of point SE for "this point is in a trial that hits the wall": 0.61 [0.59, 0.64].
- **Go/no-go: GO** (partial ρ criterion met; AUROC criterion not met, see above).

## Part 3: SE probes (H2), 9B, 1409 points / 42 trials

Full table: [`figs/probe-m5-9b.md`](figs/probe-m5-9b.md); direction for H3: `figs/direction-m5-9b.npz` (pod: `runs/m6-probe/`).
Code: `infra/semantic_entropy/probe.py` (`dump` → `extract` → `fit`).

- Activations: HF transformers forward pass on the logged prompt plus the logged response, forward hooks on all 32 decoder
  layers, at TBG (last prompt token) and SLT (last response token). Prompt token counts equal the vLLM log at all points.
- Fit: γ* = 0 bits (Kossen threshold; 30% of points have SE > 0). Logistic (C 0.05) / ridge (α 1000) on standardized
  activations; 5-fold GroupKFold by trial (no trial in both train and test); layer chosen on inner folds.

| target | features | score | control |
|---|---|---|---|
| SE > 0 (AUROC) | TBG | **0.741** (layers 18–20) | fill + turn index 0.578; shuffled labels 0.483 |
| SE (Spearman) | TBG | **0.466** (layers 20–22) | fill + turn index 0.159; shuffled −0.033 |
| SE > 0 (AUROC) | SLT | 0.648 | |
| SE (Spearman) | SLT | 0.331 | |
| SE residualized on fill (Spearman) | TBG | **0.371** | |
| trial reward < 0.5 (AUROC) | TBG | 0.671 (layer unstable: 0 or 22) | |

- **H2 supported:** SE of the coming context decision can be read from the residual stream *before* the model generates
  (TBG), well above the context-length controls, and it survives removing fill. TBG > SLT, as in Kossen et al.
- Earlier smoke test (9 trials) gave TBG 0.78; the full set gives 0.74, so the result was not driven by the dev trials.
- Caveats: (1) probes predict SE from 10 samples, so labels are noisy (most points SE 0); (2) the logistic direction and
  the diff-of-means direction at layer 20 are nearly orthogonal (cos 0.09), so for H3 steering both should be tried;
  the diff-of-means direction is the usual choice for steering. (3) Trial-reward probe is weaker and its layer is
  unstable; not a claim.
- Pod `obvrywyztadwv4` stopped after the fit (no GPU work queued). Next: 9B-RL (waits for the user), ground-truth
  harmful-edit label, H3.

