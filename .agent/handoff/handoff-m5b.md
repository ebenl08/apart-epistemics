# Handoff: M5B, Gemma 4 E4B and Ministral 3 8B on the M5 ContextBench sweep

Status (2026-11-16 ~03:15 UTC): **pod `090hikvwfs22gk` (2×A40) being set up; next, run both chains in parallel.**
No usable M5B trial data yet.

## Why

M5 showed the Qwen 3.5 9B's ContextBench success falls with context pressure
([`notes/m5-seed-sweep-results.md`](../notes/m5-seed-sweep-results.md)). M5B asks whether that holds for other families.
It runs the same KV + LogTriage sweep, with (`clm`) and without (`none`) the CLM method text.

## Models (changed on 2026-11-16, user decision)

| Family | Served name | Weights | GPU / vLLM / proxy |
|---|---|---|---|
| gemma | `gemma4-e4b` | `google/gemma-4-E4B-it` @ `4ecc2ba6`, native `gemma4` tool parser plus the `gemma4` reasoning parser (thinking on) | 0 / :8000 / :9000 |
| mistral | `ministral3-8b` | `mistralai/Ministral-3-8B-Instruct-2512-BF16` @ `f6fae979`, `mistral` parser, `--tokenizer-mode mistral` (no thinking) | 1 / :8010 / :9010 |

Both models are ungated, use native tool calls (like Qwen) and have no fallback model.

**Why the plan's Llama 3.1 8B and Gemma 3 4B → 12B were dropped:**
- The harness's whole action space is the native `bash` tool (`clm_harness/utils/tool_schemas.py:16`). Neither model drove
  it: Llama wrote mini-SWE-style text with THOUGHT and a fenced block, and Gemma 3 has no tool-call tokens.
- A fenced-bash fallback parser (`infra/fence_tool_parser.py`, still in the repo, unused now) got Llama to 89/102 parsed
  calls. Gemma 3 4B then copied the context mirror's `bash {"command": …}` notation and looped.
- Details are in `decisions.md` (the 2026-11-16 M5B entries). The failed data is on the volume in `runs/m5b-smokefail-20261115/`,
  `runs/m5b-try1-20261116/` and `runs/m5b-try2-20261116/`.

**Deviations from the plan to report:**
- The model set changed.
- Ministral 3 has no thinking, while Qwen and Gemma 4 think. The harness sends `enable_thinking: true`.

## Plan (unchanged otherwise, [`instruction-m5b.md`](../instruction-m5b.md))

Per model, `infra/m5b_launch.sh <gemma|mistral>` runs:
1. **Smoke gate:** `clm` on KV R260 s42 + LT L320 s42. It passes on ≥ 10 parsed tool calls.
   `SMOKE_ONLY=1` stops the chain after the gate.
2. **`clm`:** seeds 42–45 at N=32. The trend rule is reported only, since there is no next model.
3. **`none`:** seeds 42–43 at N=16. Add seeds 44–45 unless ≥ 13/16 trials score 0 and ≤ 2/16 trials edit.

Each family's chain stops only its own server.

## Pods

| Pod | GPUs | State | Notes |
|---|---|---|---|
| `090hikvwfs22gk` (`clm-m5b-2xa40-b`) | 2×A40, $1.18/h | running | SSH `root@194.68.245.208 -p 22095` (changes on restart) |
| `ozaojga0i4g45e` (`clm-m5b-2xa40`) | 2×A40 | stopped | Its host had no free GPUs at restart; holds the Llama/Gemma 3 weights. Terminate (ask first) |
| `sim3ebk6y0yoaw`, `hcq80a3uhg9e2n` | 1×A40 each | stopped | First attempt (Gemma 3 / Llama). Terminate (ask first) |

All pods are in EU-SE-1 on volume `hri0q37of4` at `/workspace`, set up with `SKIP_QWEN=1 infra/setup_pod.sh`.

- Copy the token to `/root/.hf_token` from `.env` `HF_TOKEN`; never print it. The repo on the volume is behind local `main`, so scp
  the `infra/` files over.
- **Don't scp `infra/semantic_entropy/*` while an M6 chain runs.**
- RunPod API, SSH and gotchas: [`handoff-semantic-entropy.md`](handoff-semantic-entropy.md).

## M6 on these models later

Notes on what `probe.py` would need (Jinja template for Gemma 4, mistral-common or vLLM `/tokenize` for Ministral) are archived in
[`archive/handoff-m6-probe-nonqwen.md`](archive/handoff-m6-probe-nonqwen.md).

## User preferences that bit here

- **Stop pods as soon as work halts.** Don't leave them idle waiting for an answer.
- **But launch the agreed next run right away.** A model whose gate passed shouldn't wait on a decision about another model.
- Estimate time per seed from the concurrency: trials in a batch run in parallel, so wall time is set by the slowest trial.
- Monitor as a checklist (done/total, GPU and CPU %) and always keep one running. Report tables in chat. Log in `decisions.md`.
- Don't change the GPU type or count without asking. Stay at or under $1.5/h.
