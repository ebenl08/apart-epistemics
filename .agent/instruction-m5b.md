# Plan: M5B, other model families on the M5 ContextBench sweep (Llama 3.1 8B, Gemma 3)

Date: 2026-11-16. Sub-experiment of M5 ([`instruction-seed-sweep.md`](instruction-seed-sweep.md),
results [`notes/m5-seed-sweep-results.md`](notes/m5-seed-sweep-results.md)). Status: **planned, awaiting user confirmation**.

## Question

Is the 9B's decline with context pressure Qwen-specific? Run the same KV + LogTriage sweep on a Llama and a Gemma model,
with and without the CLM method text.

## Config

**Control (same as M5):**
- `CB_SETTINGS=paper`: budget 32768, reserve 2048, no step cap, no nudges, T 0.7, top_p 0.95, max_tokens 8192.
- KV R260 / R1000 / R4000 / R16000 and LogTriage L320 / L1600 / L6400 / L12800, `data/cb_tasks`, timeout 28800.
- vLLM 0.33.0 BF16, max-model-len 65536, prefix caching.
- proot sandbox on the pinned M5 rootfs (`sha256:05a994d2…`).
- Every LM call logged (`runs/m5-lmlog/m5b-<model>-<skill>__<task>.jsonl`).

**Vary:**
- **Model:**
  - **Llama-3.1-8B-Instruct** on GPU0.
  - **Gemma 3 4B-it** on GPU1, with a fallback chain (below).
- **Skill `clm`:** seeds 42–45, 32 trials per model.
- **Skill `none`:** smoke at seeds 42–43 (16 trials per model). Extend to 44–45 unless the smoke is mostly 0 with almost no
  edits (rule below).

**Deviations from M5 (unavoidable):**
- No thinking mode: these models have none. `chat_template_kwargs.enable_thinking` is ignored.
- Tool calls go through vLLM's per-family parsers instead of `qwen3_coder`:
  - Llama: `llama3_json`;
  - Gemma 3: `pythonic` with vLLM's Gemma 3 tool template.

**Decision rules (fixed before the run):**
- **Smoke gate (per model, `clm`, KV R260 s42 + LogTriage L320 s42):** at least 10 parsed tool calls in the LM logs.
  - If it fails, stop that model and report; don't start its batch.
- **Gemma "decreasing":** Cochran–Armitage one-sided p < 0.05 for a decrease in success (reward ≥ 0.95) over
  log₂ pressure, on KV or LogTriage, `clm` arm. This is the M5 test.
  - If it is not decreasing: Gemma 3 12B-it, then Gemma 2 9B-it (see blocker 2).
  - `skill=none` runs only on the Gemma that ends the chain.
- **`none` smoke → keep 2 seeds** if ≥ 13/16 trials score 0 **and** ≤ 2/16 trials make any context edit. Otherwise
  add seeds 44–45.
- **Llama fallback:** Llama-3.1-8B (base) only if the Instruct smoke gate fails (see blocker 3).

## Hardware and schedule

- **One new pod: 2×RTX A6000 (48 GB each), EU-SE-1.** $0.69/h each, **$1.38/h total** (under the $1.5/h cap).
  - Template `mpye6w4gcy`, 100 GB container disk, network volume `hri0q37of4` at `/workspace`.
  - A6000 availability in EU-SE-1 is LOW (2026-11-16).
- **GPU0 (Llama):**
  1. Smoke (2).
  2. `clm` 32 (N=32).
  3. `none` smoke 16 (N=16).
  4. `none` +16 if the rule says so.
- **GPU1 (Gemma):**
  1. Smoke (2).
  2. `clm` 32.
  3. Trend test, then the fallback model if needed.
  4. `none` smoke 16, then +16 if needed.
- **Concurrency:** ≤ 32 `clm` trials per GPU. `none` at 16 for the 8–12B models (full 32k contexts; 32 caused timeouts on the 9B).
- **Estimate:** without thinking, calls are shorter than Qwen's.
  - Per GPU about 2.5–3.5 h, plus ~1.5 h per Gemma fallback model.
  - **Total about 3–5 h, about $4–7.**

## Blockers and risks

1. **HF token (blocking):** Llama 3.1 and Gemma are gated. `.env` has no `HF_TOKEN`.
   - The user adds `HF_TOKEN` to `.env` and accepts the licences on Hugging Face:
     - [meta-llama/Llama-3.1-8B-Instruct](https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct)
     - [google/gemma-3-4b-it](https://huggingface.co/google/gemma-3-4b-it)
     - [google/gemma-3-12b-it](https://huggingface.co/google/gemma-3-12b-it)
     - [google/gemma-2-9b-it](https://huggingface.co/google/gemma-2-9b-it)
   - The token goes to the pod as an env var and is never printed or committed.
2. **Gemma 2 9B has an 8k context window**, below the 32k budget. Under paper settings it can't run; budget and max-model-len
   would have to drop to ~8k, which is a different experiment. Recommend dropping it from the chain (or confirm a
   reduced-budget variant).
3. **Llama-3.1-8B base has no chat template and was not trained for tool calls.** It would mostly produce format failures,
   not context-management data. Recommend it only as a last resort.
4. **Gemma chat templates** only allow alternating user/assistant turns and have no tool role. The vLLM tool template
   handles that; the smoke gate checks it.
5. Model revisions are pinned to the HF commit SHA at download and recorded in the results note.

## Monitor

- A background loop every 60 s checks, on the pod:
  - both vLLM servers (`/v1/models` on :8000 and :8010);
  - queue progress (done/total);
  - new `exception.txt` files;
  - GPU idle ≥ 6 min;
  - GPU / CPU / RAM / disk;
  - vLLM preemptions.
- It reports on every milestone or failure, and gives a heartbeat checklist every 30 min.
