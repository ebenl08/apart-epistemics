# Handoff: M5B, Gemma 4 E4B and Ministral 3 8B on the M5 ContextBench sweep

Status (2026-11-16 15:40 UTC+8): **runs done; pod stopped.** Neither model shows Qwen's decreasing trend.

## Why

M5 showed the Qwen 3.5 9B's ContextBench success falls with context pressure
([`notes/m5-seed-sweep-results.md`](../notes/m5-seed-sweep-results.md)). M5B asks whether that holds for other families.
It runs the same KV + LogTriage sweep, with (`clm`) and without (`none`) the CLM method text.

## Results

The trend test is Cochran–Armitage, one-sided for a decreasing trend, using the success rule in `infra/cb_rules.py trend`.
Both models were run with seeds 42–45 per cell.

| Model | KV successes | KV p | LT successes | LT p | Verdict |
|---|---|---|---|---|---|
| Gemma 4 E4B | 4/16 | 0.50 | 3/16 | 0.34 | NOT_DECREASING |
| Ministral 3 8B | 8/16 | 0.19 | 1/16 | 0.88 (z = +1.19) | NOT_DECREASING |

- **Gemma 4 E4B:** weak at every pressure level. `none` (seeds 42–43) is 16/16 zero with 0 edits, so seeds 44–45 were not added.
- **Ministral 3 8B:**
  - KV is strong to R4000 and weak at R16000 by eye, but the test isn't significant with 4 seeds.
  - LT is about 0 from L1600 on; L320 gets only partial credit.
  - `none` was skipped (user, cost).
- **Per-cell rewards:** in chat 2026-11-16 15:18 UTC+8, and recomputable from `runs/m5b-{gemma4-e4b,ministral3-8b}-clm/trials/*/verifier/reward.json`.
- **Not done:** a written note in `.agent/notes/` comparing with Qwen (M5), plus a plot (`infra/cb_progress_plot.py` / `cb_report.py`).

## Models (changed on 2026-11-16, user decision)

| Family | Served name | Weights | Notes |
|---|---|---|---|
| gemma | `gemma4-e4b` | `google/gemma-4-E4B-it` @ `4ecc2ba6` | Native `gemma4` tool parser plus the `gemma4` reasoning parser (thinking on) |
| mistral | `ministral3-8b` | `mistralai/Ministral-3-8B-Instruct-2512-BF16` @ `f6fae979` | `mistral` parser with `--tokenizer-mode mistral` (no thinking); `mistral-common==1.12.0` pinned |

**Why the plan's Llama 3.1 8B and Gemma 3 were dropped:** neither could drive the harness's native-tool-only action space.
The fence parser `infra/fence_tool_parser.py` was kept but is unused. See `decisions.md`.

**Deviations from the plan to report:**
- The model set changed.
- Ministral has no thinking.
- Ministral doesn't see its own empty replies: the proxy drops them, because mistral-common rejects them.
- Ministral `none` was skipped.
- 5 Gemma `clm` trials were rerun with the same seeds after crashing in an infrastructure outage. The originals are in `runs/m5b-gemma4-outage-20261116/`.

## Infrastructure lessons (2026-11-16)

- **The network volume (MooseFS) stalled** for minutes at a time, on large writes and on single files.
  - Processes hang in `D` state and can't be killed, even with `kill -9`.
  - A hung proxy keeps its port, so `m5b_launch.sh` takes a `PROXY=<port>` override.
  - `ps`, `pgrep -af` and `tail` on volume files can hang SSH. Run probes with `setsid … > /root/file &` and read the file.
- **LM-call logs go to local disk** (`/root/m5-lmlog`). `infra/lmlog_flush.sh` appends them to `runs/m5-lmlog` when a chain exits.
  `lm_log_proxy.py` writes from a thread and falls back to `/root/lmlog-fallback`.
- **Trial folders and queue logs are still on the volume.** The volume dropped some `END` lines from a queue log, so count `verifier/reward.json` files instead.
- **Ministral needed three fixes:**
  - `send_chat_template_kwargs=false` (in `run_cb_trial.sh`);
  - the `mistral-common` pin (in `setup_pod.sh`);
  - the empty-assistant drop (in `lm_log_proxy.py`).
- **Open: 2 log files in `/root/lmlog-fallback` on pod `090hikvwfs22gk`** (lines whose volume write failed).
  Before deleting the pod, append them to `runs/m5-lmlog` (same file names), e.g. with `infra/lmlog_flush.sh /root/lmlog-fallback runs/m5-lmlog`.
  They only matter for an M6 replay.

## Pods (all stopped; terminating needs the user's OK)

| Pod | GPUs | Notes |
|---|---|---|
| `090hikvwfs22gk` (`clm-m5b-2xa40-b`) | 2×A40, $1.18/h | M5B run; holds the `/root/lmlog-fallback` files above. Last SSH `root@194.68.245.208 -p 22095` |
| `ozaojga0i4g45e` (`clm-m5b-2xa40`) | 2×A40 | Llama/Gemma 3 attempt; its host had no free GPUs at restart |
| `sim3ebk6y0yoaw`, `hcq80a3uhg9e2n` | 1×A40 each | First attempt (Gemma 3 / Llama) |

All pods are in EU-SE-1 on volume `hri0q37of4` at `/workspace`. RunPod API, SSH and gotchas: [`handoff-semantic-entropy.md`](handoff-semantic-entropy.md).

## M6 on these models later

Notes on what `probe.py` would need are in [`archive/handoff-m6-probe-nonqwen.md`](archive/handoff-m6-probe-nonqwen.md).
A Ministral replay must also drop empty assistant turns, as the proxy did.

## User preferences that bit here

- **Monitor for anomalies, not just progress.** Watch for a GPU idle with trials in flight, a proxy not responding, stale LM logs, and exceptions.
  Report every ~15 min as a checklist and notify the user on fatal anomalies.
- **Give times in UTC+8.**
- **Stop pods as soon as work halts, but launch the agreed next run right away.**
- Keep it simple. The goal is only whether other models show Qwen's behaviour.
- Cost: stay at or under $1.5/h. Don't change the GPU type or count without asking.
