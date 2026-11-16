# Handoff: M5B, Gemma 4 E4B and Ministral 3 8B on the M5 ContextBench sweep

Status (2026-11-16 20:30 UTC+8): **done. Runs finished, full report written, all M5B pods terminated.**
Neither model shows Qwen's decreasing trend. Branch: `m5b` (report, plot, analysis scripts); earlier M5B code is already on `main`.

## Read first

- Report: [`notes/m5b-results.md`](../notes/m5b-results.md) (trend + logistic tests, per-cell table, wall decomposition,
  failure modes, LM-call behaviour, caveats). Figure: [`notes/figs/m5b-vs-qwen.png`](../notes/figs/m5b-vs-qwen.png).
- Per-trial table: [`notes/figs/m5b.md`](../notes/figs/m5b.md) (`cb_report.py` output, 80 trials).
- Scripts: `infra/m5b_plot.py` (figure), `infra/m5b_analyze.py` (all report tables; usage in its docstring).

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
- **Slope vs Qwen (logistic, `success ~ model × log2 pressure + family`):** both are significantly flatter than Qwen 9B
  (interaction +0.58, p = 0.028 Gemma; +0.61, p = 0.021 Ministral) and indistinguishable from Qwen 4B (n.s.).
- **Mechanism (success = avoid the 32k wall, then answer right):**
  - Qwen 9B: walls mid-stream, rising with pressure; KV 16/16 correct when no wall.
  - Ministral: same mid-stream walls, but flat in pressure (LT 14/16 walls); KV 8/8 correct when no wall.
    382 of its 507 no-tool replies are `bash {…}` text (it imitates the rebuilt history).
  - Gemma: all 10 walls in the first 10% of the stream (never starts managing context). On completed streams it fails
    answer extraction: `tr -d ' '` on multi-word values, malformed answer tag, unescaped `grep '[WARN]'`.
- **Takeaway:** Qwen 9B's pressure drop is not elicited in these two families at 4 seeds; one fails by Qwen's mechanism
  without the trend, the other fails before context management matters.

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
- **Lost:** the 2 `/root/lmlog-fallback` files on pod `090hikvwfs22gk` went with the pod (terminated). Some LM-call
  lines are missing from `runs/m5-lmlog`; rewards and trial folders are complete. Only matters for an M6 replay.
- **Report data was extracted on M6 pod `rckduvamr1vclf`** (volume mounted, `nice`/`ionice`), not a new pod: pack
  small per-trial files + summarise LM logs into `lmlog_summary.jsonl`, then `cb_report.py` locally (needs
  `data/cb_tasks/*/task.toml` copied in, gitignored). The extraction script is described in the report's Reproduce section.

## Pods

All four M5B pods (`090hikvwfs22gk`, `ozaojga0i4g45e`, `sim3ebk6y0yoaw`, `hcq80a3uhg9e2n`) are **terminated** (user OK).
Data lives on volume `hri0q37of4` (EU-SE-1) under `runs/m5b-*` and `runs/m5-lmlog/m5b-*`. RunPod API, SSH and gotchas: [`handoff-semantic-entropy.md`](handoff-semantic-entropy.md).

## Possible next steps (none agreed)

- More seeds (8, as M5) for Ministral KV, the only cell with a visible-by-eye drop (R16000), to tighten its slope.
- A fixed Gemma prompt/answer format is out of scope: it would test the harness, not pressure.

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
