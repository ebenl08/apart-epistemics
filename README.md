# Uncertainty in Context Management: Do Context Language Models Know What to Forget?

Apart Research [AI × Epistemics Sprint](https://apartresearch.com/sprints/ai-x-epistemics-research-sprint-2026-11-13-to-20) (Track 4, Open Track), November 2026.

## Motivation

[Context Language Models](https://arxiv.org/abs/2609.37725) (CLMs) manage their own context: the transcript is a
file the model edits, deleting stale turns or offloading them to disk. Context management thus moves from the
harness into the model itself. We ask whether the model *knows* what to keep, cut or offload, and whether failures
of context management under pressure are linked to the model's **epistemic uncertainty** about those decisions.
If they are, uncertainty could be measured, monitored and thresholded (for example, refusing to delete when
uncertain) to make context management safer.

## Narrative

**Experiment 1 — Eliciting the performance drop (reimplementation).** We reimplement CLMs on
[ContextBench](https://github.com/RulinShao/ContextBench) (KV store, LogTriage) with Qwen3.5-4B, Qwen3.5-9B and an
RL-trained 9B CLM checkpoint, sweeping context pressure over four levels (8 seeds per cell, `skill=clm`, plus a
`skill=none` arm). The 9B's reward falls steadily with pressure (KV 0.95 → 0.12; LogTriage 0.83 → 0.18) while the
4B's does not (model × pressure interaction p = 0.027); the failure is context management (hitting the context
budget), not retrieval. The RL checkpoint has the same slope at a higher level.

**Experiment 2 — Uncertainty predicts failure.** We replay 42 logged trials per model byte-exactly, resample 10
replies at each of ~1,400 decision points, execute every sampled command in a reconstructed sandbox, and cluster
samples by their effect on the context (keep / edit / offload / delete per block). Discrete **semantic entropy (SE)**
over these clusters predicts lower reward at fixed pressure: partial Spearman ρ = −0.59 (9B) and −0.48 (9B-RL).
The result holds for **decision-only SE**, which excludes failed commands and malformed tool calls
(ρ = −0.50 / −0.45). RL training removes most uncertainty, but the uncertainty that remains still predicts failure.

**Experiment 3 — Uncertainty is linearly decodable.** A linear probe on the residual stream at the last prompt
token, before the model generates anything, predicts whether a decision will be uncertain: AUROC 0.74 (9B) and
0.82 (9B-RL), and 0.77 / 0.81 for decision-only SE, against 0.52 / 0.49 for a context-length baseline.

**Work in progress**
- **Causality (H3, WIP):** directional ablation of the SE direction by weight orthogonalization. Preliminary: halving
  the direction lowers decision uncertainty in LogTriage with tool use intact; removing it breaks tool-call
  formatting. The direction is partly confounded with context length, so a cleaned direction and a matched control
  are planned ([plan](.agent/instruction-h3-clean.md), [handoff](.agent/handoff/handoff-m6-causality.md)).
- **Other models (WIP):** Gemma, Llama and Ministral on the same sweep ([notes](.agent/notes/m5b-results.md));
  not part of the experiments above.

Write-up draft: [`.agent/notes/m6-se-paper.md`](.agent/notes/m6-se-paper.md); LaTeX in [`paper/`](paper/).
Paper handoff (all numbers and sources): [`.agent/handoff/handoff-m6-paper.md`](.agent/handoff/handoff-m6-paper.md).

## Repository layout

| path | contents |
|---|---|
| [`context-language-models/`](context-language-models/) | the CLM harness and ContextBench agent (vendored from the CLM authors, CC BY-NC 4.0) |
| [`infra/`](infra/) | pod setup, vLLM serving, logging proxy, trial runners (Experiment 1) |
| [`infra/semantic_entropy/`](infra/semantic_entropy/) | SE collection, analysis, probes, ablation (Experiments 2–3, H3) |
| [`.agent/`](.agent/) | plans (`instruction-*.md`), results notes (`notes/`), decision log, handoffs |
| `data/`, `runs/` | task data and all run outputs (gitignored; kept on the network volume) |

## Reproducing the results

The scripts assume a RunPod GPU pod (we used 1×A40, 48 GB) with a network volume mounted so that the repo is at
`/workspace/apart-epistemics`; paths are hard-coded to it. Commands below run from that directory.

**Setup**
```bash
bash infra/setup_pod.sh            # proot, venvs (/root/envs/{vllm-env,clm-env,hf}), Qwen3.5-4B/9B weights, pinned rootfs
# 9B-RL weights (pinned revision):
/root/envs/hf/bin/hf download context-language-model/rl-ckpt-livectx_dapo-iter44 \
  --revision ffc4aab2f30cb5b802ced6c84e6590ab5fec213d --include "converted/*" --local-dir /root/models/clm-9b-rl
cp infra/semantic_entropy/m6env.sh /root/m6env.sh
```
ContextBench tasks go in `data/cb_tasks/` (copied from ContextBench's prebuilt `tasks/` for seeds 42–49, timeout
raised to 28800 s; see [`.agent/handoff/handoff-reimplementation.md`](.agent/handoff/handoff-reimplementation.md)).

**Experiment 1 (pressure sweep).** Serve the model, put the logging proxy in front of it (Experiments 2–3 replay
these logs), and run a queue of trials (one line per trial: `MODEL SKILL TASK RUN_DIR`):
```bash
PORT=8000 infra/serve_qwen35_9b.sh &                                         # or serve_qwen35_4b.sh
python infra/lm_log_proxy.py 9000 http://localhost:8000 runs/m5-lmlog &      # full request/response log per trial
API_BASE_PREFIX=http://localhost:9000 infra/run_queue.sh runs/queues/m5-9b.txt 40
python infra/cb_report.py --out runs/m5-report runs/m5-4b runs/m5-9b runs/m5-9b-rl   # table + reward vs pressure
```
Plan and settings: [`.agent/instruction-seed-sweep.md`](.agent/instruction-seed-sweep.md); results:
[`.agent/notes/m5-seed-sweep-results.md`](.agent/notes/m5-seed-sweep-results.md).

**Experiments 2 and 3 (SE and probes), one model unattended.** `runs/m6-se/queue-9b.txt` lists the 42 logged 9B
trials (`runs/m5-lmlog/m5-9b__<task>.jsonl`); the chain serves the model, replays (Gate A), samples K = 10, executes
and labels (Gate B), runs the correlation analysis, then extracts activations and fits the probes:
```bash
# arguments: <queue name> <run prefix> <weights> <served name>; the queue name must differ from "9b"
# (the chain derives queue-<name>.txt from queue-9b.txt)
HF_HOME=/root/hf_cache infra/semantic_entropy/m6_chain.sh 9bre  m5-9b    Qwen/Qwen3.5-9B                   qwen35-9b
infra/semantic_entropy/m6_chain.sh                        9brl  m5-9b-rl /root/models/clm-9b-rl/converted  qwen35-9b-rl
infra/semantic_entropy/m6_status.sh 9brl                  # progress checklist
```
Step by step: `collect.py {replay,points,sample,execute}` → `analyze.py <prefix> runs/m6-se/analysis` (Experiment 2)
→ `probe.py {dump,extract,fit} <prefix>` (Experiment 3). Decision-only SE (robustness for both):
`decision_only.py h1`, then `decision_only.py h2`. Method: [`.agent/instruction-semantic-entropy.md`](.agent/instruction-semantic-entropy.md)
(Parts 1–3 and the post-hoc amendment). Runtime per model: ~2 h of sampling + ~1 h of probes on one A40.

**H3 (WIP).** `ablate.py make <base weights> <direction> <λ> <out>` writes an edited checkpoint; `h3_sub.sh` /
`h3_rs.sh` run a condition on the 16-trial subset; `h3_analyze.py` compares it with the baseline. See the
[causality handoff](.agent/handoff/handoff-m6-causality.md).

## Acknowledgements

This project builds directly on **Context Language Models** by Rulin Shao, Shannon Zejiang Shen, Junjie Oscar Yin,
Yuetai Li, Minheng Wang, Hamish Ivison, Radha Poovendran, Nathan Lambert, Teng Xiao, Mike Lewis, Wen-tau Yih,
Luke Zettlemoyer and Pang Wei Koh. We use their CLM harness, the ContextBench benchmark and their released RL
checkpoint, vendored in [`context-language-models/`](context-language-models/) under its
[CC BY-NC 4.0 license](context-language-models/LICENSE). We thank the authors for releasing code, data and models.
The harness runs on [Harbor](https://github.com/laude-institute/harbor). Our uncertainty measure follows semantic
entropy ([Kuhn et al., 2023](https://arxiv.org/abs/2302.09664); [Farquhar et al., 2024](https://pmc.ncbi.nlm.nih.gov/articles/PMC11186750))
and semantic entropy probes ([Kossen et al., 2024](https://arxiv.org/abs/2406.15927)).

## Citation

If you use this work, please cite the CLM paper it builds on:

```bibtex
@article{shao2026context,
  title   = {Context Language Models},
  author  = {Shao, Rulin and Shen, Shannon Zejiang and Yin, Junjie Oscar and Li, Yuetai and
             Wang, Minheng and Ivison, Hamish and Poovendran, Radha and Lambert, Nathan and
             Xiao, Teng and Lewis, Mike and Yih, Wen-tau and Zettlemoyer, Luke and Koh, Pang Wei},
  journal = {arXiv preprint arXiv:2609.37725},
  year    = {2026}
}
```
