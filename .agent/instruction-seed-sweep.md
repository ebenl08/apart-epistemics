# Plan: M5 seed sweep on ContextBench (4B vs 9B vs 9B-RL)

Date: 2026-11-15. Scope: ContextBench only (BCP paused, user request).
Inputs: [`notes/m2-contextbench-results.md`](notes/m2-contextbench-results.md),
[`handoff/handoff-reimplementation.md`](handoff/handoff-reimplementation.md).

## Goal

1. **Main question:** does the 9B score go down steadily as context pressure goes up, while the
   4B holds up? Use enough seeds that the answer is not noise.
2. **If yes**, the failed trials (budget wall from build-up of the model's own old turns) become
   the labels for step 2. Uncertainty scores at each edit are then checked against those
   failures.
3. **New arm: the paper's RL-trained 9B.** Does RL training on context management carry over to
   ContextBench?

## Where we start (from M2)

| Family | Model | R/L 0.5x | ~1.5–2x | ~6–8x | ~16–24x | Seeds |
|---|---|---|---|---|---|---|
| KV | 4B | 0.94 | 1.00 | 0.50 | 1.00 | 2 / 4 / 4 / 4 |
| KV | 9B | 1.00 | 0.74 | 0.56 | 0.00 | 2 / 4 / 4 / 4 |
| LogTriage | 4B | 1.00 | 1.00 | 1.00 | 0.48 | 2 each |
| LogTriage | 9B | 0.50 | 0.50 | 0.00 | 0.25 | 2 each |
| Needle | 4B | 1.00 | 0.10 | 0.68 | 0.26 | 2 each |
| Needle | 9B | 1.00 | 0.98 | 0.55 | 0.36 | 2 each |

M2 trial counts: 60 main-run trials (30 per model). Seeds 42 and 43 cover 12 trials each
(3 families × 4 levels); seeds 44 and 45 cover KV R1000 / R4000 / R16000 only (3 trials each).
Plus 15 smoke-grid trials.

- The 9B already trends down on KV and Needle.
- The 4B's KV R4000 result (2 seeds at 1.0, then 2 at 0.0) shows that n ≤ 4 cannot tell a
  trend from noise.

## The 9B RL checkpoint (pinned)

- **Repo:** [`context-language-model/rl-ckpt-livectx_dapo-iter44`](https://huggingface.co/context-language-model/rl-ckpt-livectx_dapo-iter44).
- **Pinned revision:** `ffc4aab2f30cb5b802ced6c84e6590ab5fec213d` (repo last modified 2026-09-17).
- **Weights:** in the `converted/` subfolder. 4 safetensors shards, 19.3 GB, BF16,
  `Qwen3_5ForConditionalGeneration`, 32 layers, hidden 4096. A chat template is included.
- **Which arm it is:** the README calls it the "LiveCtx arm's table checkpoint (tab:rl_results)",
  i.e. the CLM arm of the paper's RL table: BCP 28.8 → 42.5.
- **Base model:** the card says `Qwen/Qwen3.5-9B-Base`.
- **How it was trained:** GRPO on 3,040 OpenResearcher deep-research prompts, 70 steps, 32K
  budget (paper, App. "Reinforcement learning").
  - It was never trained on ContextBench, so on ContextBench it is a **transfer test**, not an
    in-distribution reproduction.
- **Not used:** the sibling repo
  [`rl-ckpt-b0sum_dapo-iter49`](https://huggingface.co/context-language-model/rl-ckpt-b0sum_dapo-iter49)
  (pinned `4a35d932e1112a2a9d98e9ca41f3c2c5f0cc2284`) is the summary-harness arm, so it is not a CLM.
- **Download:**
  ```bash
  huggingface-cli download context-language-model/rl-ckpt-livectx_dapo-iter44 \
    --revision ffc4aab2f30cb5b802ced6c84e6590ab5fec213d --include "converted/*" \
    --local-dir /root/models/clm-9b-rl
  # serve /root/models/clm-9b-rl/converted as qwen35-9b-rl, same flags as serve_qwen35_9b.sh
  ```
- **Smoke test first (gate):** run KV R260 and LogTriage L320, seed 42.
  - Check: tool calls parse with `qwen3_coder` / `qwen3`, thinking appears, and at least one edit
    is accepted.
  - If tool calls do not parse, check the chat template before running the full batch.

## Experiment config

**Control (unchanged from M2):**
- `CB_SETTINGS=paper`: budget 32768, reserve 2048, no step cap, no nudges, T 0.7, top_p 0.95,
  max_tokens 8192, thinking on.
- `skill=clm` (the paper's method text for each family).
- vLLM 0.33.0, BF16, max-model-len 65536, prefix caching on.
- proot sandbox, timeout 28800 s.
- Levels are the same as M2: KV R260 / R1000 / R4000 / R16000; LogTriage L320 / L1600 / L6400 /
  L12800; Needle K4-C4 / K4-C24 / K8-C60 / K2-C192.

**Vary:**
- **Model: 4B / 9B / ==9B-RL (new)==.**
- **Seeds: ==8 per level per model== (now 2–4).**
  - New seeds: 46–49 where 42–45 already exist, and 44–49 where only 42–43 exist.
  - The 9B-RL arm runs seeds 42–49.
- Family: **KV and LogTriage (core)**, Needle (optional).
  - The 4B Needle score mostly measures whether it copies the needle-keeping step of the recipe
    correctly, not memory under pressure. So Needle is only clean for the 9B arms.

**Key changes vs M2:**
- the RL arm;
- 8 seeds;
- **full logging of every LM call**, needed for step 2 (see Prerequisites).

## Trial count

| Block | 4B new | 9B new | 9B-RL new | Total |
|---|---|---|---|---|
| KV | 6 + 4×3 = 18 | 18 | 32 | **68** |
| LogTriage | 6×4 = 24 | 24 | 32 | **80** |
| Needle (optional) | 24 | 24 | 32 | 80 |
| **Core (KV + LT)** | 42 | 42 | 64 | **148** |

## Time estimate

**Basis (revised 2026-11-15):**
- My first estimate capped each GPU at 16 concurrent trials. That was wrong: "100% GPU util"
  only means a kernel is always running, not that throughput is maxed out.
- vLLM batches every request in flight. The 4B server has a 945k-token KV cache; at 15-25k
  context per trial that holds ~40-60 trials at once. More trials in a batch means more
  tokens/s in total.
- Evidence from M2: on the 4B server, 24 ContextBench trials, the BCP smoke (5) and BCP
  50-question runs (up to ~23 at once) all fit in ~1.5 h (18:23-19:52). The 9B's 24 trials plus
  the smoke grid took ~1.5 h (19:54-21:22).
- So: **launch every trial of a model at once (`run_queue.sh` N=48, longest first)**. A batch
  then takes about as long as its longest trial, which is a chain of LM calls one after another
  and cannot be parallelized:
  - LogTriage L12800 (~290 calls): 55-75 min;
  - KV R16000 (~210 calls): ~30 min for the 4B, ~45-60 min if a 9B arm finishes the stream
    instead of hitting the wall early.
- Add ~20-30% for the larger batch.
- **Check `vllm:num_preemptions_total` in the first 10 min.** If the KV cache fills, vLLM
  preempts requests and the trials slow down; then lower N.

**Measured in M2 (one A40, 8–23 trials on the server at once, everything done in ~4.5 h,
18:23–22:49 UTC):**

Each family's 8 trials (4 levels × seeds 42 / 43) were launched together, so a batch took about
as long as its slowest trial, which is the highest level that did not hit the budget wall.

| Batch (8 trials) | Window (UTC) | Wall clock | Slowest trial | Shared the GPU with |
|---|---|---|---|---|
| KV, 4B | 18:23–18:53 | 30 min | R16000 s42, 29.6 min | 5 BCP smoke trials |
| Needle, 4B | 18:52–19:50 | 58 min | K2-C192 s43, 52.0 min | LogTriage 4B, BCP 50 (4B) |
| LogTriage, 4B | 18:52–19:52 | 60 min | L12800 s43, 59.7 min | Needle 4B, BCP 50 (4B) |
| KV, 9B | 19:54–20:35 | 41 min | R16000 s42, 34.7 min | 9B smoke grid, LogTriage / Needle 9B |
| Needle, 9B | 20:08–21:10 | 62 min | K2-C192 s43, 61.9 min | KV / LogTriage 9B, extra seeds |
| LogTriage, 9B | 20:08–21:22 | 74 min | L12800 s43, 74.5 min | KV / Needle 9B, BCP 50 (9B), up to 23 trials |
| KV seeds 44 / 45, both models (12 trials) | 20:34–22:49 | 2 h 15 min | ≤ 26 min | ran in waves, not all at once (see below) |

Mean minutes per trial by level (inflated by GPU sharing):

| Level | 4B | 9B |
|---|---|---|
| KV R260 / R1000 / R4000 / R16000 | 5 / 6 / 10 / 26 | 8 / 15 / 22 / 20 |
| LogTriage L320 / L1600 / L6400 / L12800 | 14 / 45 / 47 / 57 | 23 / 37 / 36 / 56 |
| Needle K4-C4 / K4-C24 / K8-C60 / K2-C192 | 3 / 21 / 39 / 28 | 3 / 14 / 20 / 42 |

- Low levels finish in minutes and free their slots; the batch then waits on its largest level.
- The longest trial is the one with the most ops that does not hit the wall: LogTriage L12800 s43
  ran all 262 ops in 289 LM calls. A trial that hits the wall ends early and shortens the batch
  (9B KV R16000 s45: dead at op 16 after 6.3 min). That is why 9B R16000 averages less time than
  4B R16000. If more 9B trials finish the stream in M5, expect longer batches.
- Concurrency slows every trial: vLLM decoded ~170 tok/s in total across ~11 requests (Needle 4B
  run), so one long thinking turn could take minutes.
- The seeds 44 / 45 window (2 h 15 min for trials of ≤ 26 min each) means those trials ran in
  waves, probably waiting for their model's server, since only one model is served at a time
  on :8000. The trial start times in `runs/m2-kv-{9b-,}clm-s4445/` on the pod show the real
  schedule. In M5, launch each model's trials only while that model is being served.
- Summed per-trial minutes (4B 686, 9B 704, smoke 148) are not GPU time: the trials overlapped.

**Per-model batch, core (KV + LT, all trials launched together):**

| Batch | Trials | Longest trial | Wall time |
|---|---|---|---|
| 4B | 42 | L12800 ~60 min | **~1.1-1.3 h** |
| 9B | 42 | L12800 ~75 min | **~1.2-1.5 h** |
| 9B-RL | 62 + 2 smoke | unknown, assume like 9B | **~1.3-1.6 h** (+15 min smoke) |
| Needle (optional) | +24 / 24 / 32 | K2-C192 ~60 min | goes into the same batch, ~+10-20% |

**Fixed overhead:**
- server swap: ~5 min each;
- RL download: ~10 min;
- packaging the new seeds: ~10 min;
- the logging prerequisite: ~0.5 h.

## 1 vs 2 vs 3 A40s

Each model needs its own vLLM server. Putting two models on one A40 leaves too little KV cache
(weights alone: 8 + 17 + 17 GB of 46).

| Option | Layout | Setup | Wall time, core (+ Needle) | GPU-h billed |
|---|---|---|---|---|
| **1×A40, current pod** | 4B → 9B → 9B-RL, each a fully parallel batch | 0 | **~4.5 h (~5 h)** incl. overhead | ~4.5 |
| 2×A40, new pod | GPU0: 4B → 9B; GPU1: RL smoke → 9B-RL | ~1 h rebuild | ~3.5 h | ~7 |
| 3×A40, new pod | one model per GPU, all at once | ~1 h rebuild | ~3 h | ~9 |

**Recommendation: stay on the current 1×A40 pod.**
- Once every batch runs in parallel, extra GPUs save only ~1-1.5 h, and rebuilding the
  environment eats most of that (proot, rootfs, venvs, data). Rebuilding also risks hitting
  day-1 problems again.
- Order: RL download + smoke test → 4B batch → 9B batch → 9B-RL batch.
- Write up each batch while the next one runs.
- Go multi-GPU only if a new pod is available right away **and** someone else rebuilds the
  environment in parallel.

**If multi-GPU anyway:**
- one vLLM server per GPU (`CUDA_VISIBLE_DEVICES=i`, ports 8000/8001/8002). No tensor
  parallelism: the 9B fits on one A40;
- a one-line change in `infra/run_cb_trial.sh`: `api_base` is hard-coded to `:8000`, so read
  `API_BASE` from the environment;
- **pod size:** ≥ 100 GB container disk (we have 9 GB free now, and the RL weights alone are
  19.3 GB) and ≥ 256 GB RAM.
  - RAM reached 147 GB at ~20 trials in M2. 48 concurrent trials have not been tested, so log it
    with `util_log.sh`.

**On 1 GPU, disk is a blocker:** `/` has ~9–11 GB free. Either put the RL weights on `/workspace`
(~24 GB free there), or delete the 9B instruct weights after the 9B batch.

## Prerequisites (before launching)

1. **Log every LM call (prompt + response + token counts) to disk.**
   - Right now the model's own edits delete earlier commands from the saved trajectory (see
     Gotchas in the handoff).
   - Step 2 needs the full context state at every edit turn, to replay it and resample it.
   - Without this, these 148 trials give accuracy only, and nothing usable for uncertainty.
   - Cheapest way: a small logging proxy in front of vLLM, or a litellm success callback.
     Verify on one smoke trial.
2. Package the new seeds (`data/cb_tasks/`, same packaging script as seeds 44 / 45).
3. Run the RL smoke test (gate above).

## Analysis (decide before the runs)

1. **Main result:** reward against log₂ pressure for each model and family, mean ± bootstrap 95%
   CI over the 8 seeds.
2. **Test for "the 9B goes down":** a one-sided Cochran–Armitage trend test on success
   (reward ≥ 0.95) across the 4 levels, per family. Also a logistic model, success ~ model ×
   log-pressure + family, where the **interaction term** answers "the 9B falls faster than the
   4B".
3. Also report the **budget-wall rate** for each cell. This is the failure label used in step 2.
4. **How many seeds is enough:** with 8 seeds, a fall from ~1.0 to ~0.25 (the 9B on KV) is
   clearly detectable. A difference at a single level such as R4000 (0.50 vs 0.56) is not, and we
   will not claim one.

## Outputs

- `notes/m5-seed-sweep-results.md`:
  - per-trial tables;
  - plots with all 3 arms;
  - the trend tests.
- A `decisions.md` entry.
- Ask before every commit.
