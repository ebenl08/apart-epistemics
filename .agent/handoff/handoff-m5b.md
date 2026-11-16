# Handoff: M5B, Llama 3.1 8B and Gemma 3 on the M5 ContextBench sweep

Status (2026-11-16): **fix built locally, not yet run.** Both old pods are stopped; no M5B trial data yet.
Next steps:
1. Wait until the M6 run on the volume is done (`probe.py` copy rule, see below).
2. Confirm the config with the user.
3. Create one 2×A40 pod and run the smoke gate on both families.

## Why

M5 showed the Qwen 3.5 9B's ContextBench success falls with context pressure
([`notes/m5-seed-sweep-results.md`](../notes/m5-seed-sweep-results.md)). M5B asks whether that holds for other families.
It runs the same KV + LogTriage sweep, with (`clm`) and without (`none`) the CLM method text.

## Plan (agreed with the user)

The full plan is in [`instruction-m5b.md`](../instruction-m5b.md). Changes since it was written:
- **Gemma 2 9B dropped** (8k context, below the 32k budget). The Gemma chain is **3 4B → 3 12B**.
- **Llama base fallback dropped.**
- **Two 1×A40 pods instead of one 2×A6000.** No A6000 was free in secure cloud, and the user approved A40. That is $0.59/h each, $1.18/h total.

Per model:
1. **Smoke gate:** `clm` on KV R260 s42 + LT L320 s42. It passes on ≥ 10 parsed tool calls.
2. **`clm`:** seeds 42–45 at N=32.
3. **Gemma only:** if the Cochran–Armitage trend test isn't decreasing (p ≥ 0.05 on both families), move to the next model in the chain.
4. **`none`:** seeds 42–43 at N=16. Add seeds 44–45 unless ≥ 13/16 trials score 0 and ≤ 2/16 trials edit.

All of this is automated by `infra/m5b_launch.sh <gemma|llama>`, which needs `infra/cb_rules.py` (`selftest` passes).

## What happened

Times are UTC (the user is in GMT+8).

| When | Event |
|---|---|
| 2026-11-15 18:34 | Llama 3.1 access approved on HF (Gemma already approved). The token is fine-grained and works. |
| 18:37 / 18:38 | Pods created: `sim3ebk6y0yoaw` (Gemma) and `hcq80a3uhg9e2n` (Llama). Setup finished; weights downloaded at pinned revisions. |
| ~18:45 | **Smoke gate failed on both: 0 parsed tool calls.** Trials killed; both scripts exited `SMOKE_GATE_FAILED`. |
| 18:45 → 2026-11-16 01:22 | **Pods left idle with vLLM loaded (~6.7 h, ~$8 wasted)** while waiting for the user. Stopped at 01:22. Rule now: stop pods whenever work halts. |

The `decisions.md` headings for the M5B launch and smoke-gate failure say 2026-11-16, but those events were on 2026-11-15 UTC.

### Why the gate failed

The harness's whole action space is one native tool, `bash`
(`context-language-models/clm/clm_harness/utils/tool_schemas.py:16`). Context edits are bash commands too. If a reply
has no `tool_calls`, the harness sends "(No tool call in your last turn. When ready, issue your next `bash` command…)".
Both trials were stuck at op 1.

- **Llama 3.1 8B** (`llama3_json` parser, vLLM v0.33.0 `tool_chat_template_llama3.1_json.jinja`):
  - It replies "THOUGHT: … ```bash … ```" as plain text, so the parser finds nothing.
  - That layout is mini-SWE-agent's. Open question: does the CLM skill text or task prompt show that format, so the model is copying it? Check before building the fix.
- **Gemma 3 4B** (`pythonic` parser, `--language-model-only`, vLLM `tool_chat_template_gemma3_pythonic.jinja`):
  - 114 HTTP 400s with "Conversation roles must alternate user/assistant…". The harness sends `system, user, user`.
  - When a call gets through, the model writes a fenced ```bash block, not a pythonic call.

Evidence on the volume:
- `runs/logs/m5b-{gemma,llama}.log` (launch logs ending in `SMOKE_GATE_FAILED`);
- `runs/logs/vllm-m5b-*.log`;
- `runs/m5-lmlog/m5b-*-clm__*.jsonl`;
- `runs/m5b-*-clm/` (killed smoke trials; delete or move them before rerunning).

## Fix (built 2026-11-16, details in `decisions.md`)

- `infra/fence_tool_parser.py` is a vLLM plugin with two parsers, `llama3_json_fence` and `pythonic_fence`:
  - It takes the last ```bash block first and falls back to the native parser when there is none.
  - `content` is the text before the block, and the call id is `fence_<hex>`.
  - Each reply logs one `FENCE kind=fallback|native|miss` line in the vLLM log.
  - Self-check: `python3 infra/fence_tool_parser.py`.
- `infra/chat_templates/*` are patched:
  - A `fence_` call replays as the generated text.
  - Gemma's same-role turns are merged (this fixes the 400s).
  - The Llama date is fixed.
- `serve_m5b.sh` uses the plugin.
- `m5b_launch.sh <family>` runs one family per GPU (Gemma: GPU 0, :8000, proxy :9000; Llama: GPU 1, :8010, proxy :9010). It kills only its own server. The smoke line prints the FENCE counts and how many `fence_` ids were replayed.
- **Smoke checks beyond the existing ≥ 10-calls gate:**
  - Most calls should be `fallback`, with few `miss`.
  - `fence ids replayed` > 0, which shows the harness kept the ids and the template took the fence branch.
  - Token-level round trip on a few logged turns: the vLLM tokenizer with `chat_template=<patched>` should give `prompt_tokens` equal to the logged value.
- **Deviation to report:** Llama and Gemma use text-parsed actions, while Qwen uses native calls.
  - The Qwen text-path control (1 seed × 16 cells) is still optional and not approved.
- **M6 `probe.py` changes are in the M6 session's hands:** see [`handoff-m6-probe-nonqwen.md`](handoff-m6-probe-nonqwen.md).
  - **Don't scp `infra/semantic_entropy/*` to the volume while an M6 chain runs.** M5B needs only `fence_tool_parser.py`,
    `chat_templates/`, `serve_m5b.sh` and `m5b_launch.sh`, and none of these are M6 files.
- Delete or move `runs/m5b-*-clm/` and `runs/m5-lmlog/m5b-*` (the failed smoke trials) before rerunning.

## Pods

**Plan: one new 2×A40 pod** (EU-SE-1, volume `hri0q37of4` at `/workspace`, ~$1.18/h), with `SKIP_QWEN=1 infra/setup_pod.sh`.
Use the pod JSON template in the semantic-entropy handoff with `"gpu":{"count":2}`. The weights must be downloaded
again on the new container disk, which `serve_m5b.sh` does at the pinned revision. The old 1×A40 pods below are stopped; terminate them
once the new pod works (ask first).

| Pod | Name | Holds | Last SSH |
|---|---|---|---|
| `sim3ebk6y0yoaw` | `clm-m5b-gemma` | gemma-3-4b-it @ 093f9f38, gemma-3-12b-it @ 96b6f1ec (downloaded on first serve) | `root@194.68.245.118 -p 22147` |
| `hcq80a3uhg9e2n` | `clm-m5b-llama` | Llama-3.1-8B-Instruct @ 0e9e39f2 | `root@194.68.245.201 -p 22172` |

Copy the token to the pod as `/root/.hf_token` from `.env` `HF_TOKEN`; never print it. The repo on the volume is behind local
`main`; scp the `infra/` files below over.
RunPod API, SSH and gotchas (activate `vllm-env` before `vllm serve`, cgroup v1 CPU, no `timeout` on macOS):
[`handoff-semantic-entropy.md`](handoff-semantic-entropy.md).

## Files (uncommitted, ask before committing)

- `infra/serve_m5b.sh`: downloads at the pinned revision and serves (`llama31-8b`, `gemma3-4b`, `gemma3-12b`), with `PORT`, max-model-len 65536.
- `infra/m5b_launch.sh`: the per-family chain above.
- `infra/cb_rules.py`: `trend` and `none-smoke` decision rules, plus `selftest`.
- `infra/chat_templates/`: vLLM v0.33.0 Llama 3.1 JSON and Gemma 3 pythonic tool templates.
- `infra/setup_pod.sh`: adds `SKIP_QWEN=1`.
- `.agent/instruction-m5b.md`: the plan (committed with the M6 work).

## User preferences that bit here

- **Stop pods as soon as work halts.** Don't leave them idle waiting for an answer.
- Estimate time per seed from the concurrency: trials in a batch run in parallel, so wall time is set by the slowest trial.
- Monitor as a checklist (done/total, GPU and CPU %) and always keep one running. Report tables in chat. Log in `decisions.md`.
- Don't change the GPU type or count without asking. Stay at or under $1.5/h.
