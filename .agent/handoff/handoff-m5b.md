# Handoff: M5B, Llama 3.1 8B and Gemma 3 on the M5 ContextBench sweep

Status (2026-11-16 01:25 UTC): **blocked at the smoke gate; both pods stopped.** No M5B trial data yet.
Next step: build the tool-call fix (below) locally, then restart the pods and rerun the smoke gate.

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

## Proposed fix (user said "fix it"; config not yet confirmed)

**A. Fenced-bash fallback parser (recommended)**
- A vLLM `--tool-parser-plugin` that first tries the family's native parser.
- If that finds no tool call, it turns the last fenced ```bash block into `bash(command=…)`.
- **For Gemma, also stop the 400s.** Either use a chat template that merges consecutive same-role messages, or merge them in `lm_log_proxy.py`. The template is cleaner, since the proxy logs what it receives.
- **Log every fallback and every parse miss** (no block, several blocks, truncated block), so a format failure can be told apart from a context-management failure.
- Check whether the harness calls vLLM with streaming. If it does, the plugin needs the streaming method too.
- Self-check: a `__main__` with sample Llama and Gemma replies.

**Consequences, discussed with the user**
- Llama and Gemma read text-parsed actions, while Qwen used native calls. Family differences could partly come from the format. Record this as a deviation.
- Optional control (not yet approved): run Qwen 9B through the same text path, 1 seed × 16 cells. All 16 trials run at once, so it takes about 45–60 min (~$0.5), not 2 h. The user pushed back on a 2 h estimate.
- The model's prompt and sampling are unchanged, and M6 semantic entropy is unaffected (the command text is sampled either way).
- Standard practice: mini-SWE-agent parses ```bash blocks; OpenHands has a non-function-calling mode. Pick the mode per model and report it.

**Alternatives the user has seen:**
- **B.** Tell the models in the prompt to use tool calls. This is a bigger deviation.
- **C.** Report "can't drive the harness" as the finding.
- **OpenRouter:**
  - Llama 3.1 8B has tool calling on CoreWeave, and Gemma 3 12B on DeepInfra. Gemma 3 4B has no provider with tool calling.
  - The sandbox would still need a CPU pod.
  - No hidden states or n>1 samples for M6.

**Before running, confirm the config with the user** (bulleted control/vary). Then:
1. Build and test the parser locally.
2. Restart the pods.
3. Rerun the smoke gate with a monitor.
4. Run the rest of the chain unattended.

## Pods

Both pods are 1×A40, EU-SE-1, $0.59/h, on volume `hri0q37of4` at `/workspace`, and both are **stopped**. Restart with `POST /v2/pods/<id>/action {"action":"start"}`. That keeps the container disk (venvs, `/root/models/*`, `/root/.hf_token`), but SSH ip and port change. If the host has no free GPU, create a new 1×A40 pod from the JSON in the old session's scratchpad (or the template in the semantic-entropy handoff) and run `SKIP_QWEN=1 infra/setup_pod.sh`.

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
