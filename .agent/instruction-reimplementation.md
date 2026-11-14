# Experiment: reimplement CLM baselines with Qwen3.5-4B

Written: 2026-11-14. Status: planned, nothing run.
Repo: `context-language-models/` (project root). Paper: `Context Language Models.pdf` (arXiv 2609.37725).

## Goal

Get CLM running end-to-end on ContextBench and BrowseComp-Plus (BCP) with a model small enough for mech interp, and confirm the pipeline is correct before the elicitation experiment (step 2 of `query.md`).

"Correct" here does not mean matching the paper's numbers. The paper used Qwen3.6-27B, so 4B numbers will be lower. It means:
1. Runs finish and are graded with the paper's settings.
2. Sanity checks hold (see step 3).
3. Optional: a small Qwen3.6-27B calibration subset lands near the paper's numbers.

## Model: Qwen3.5-4B

- HF: https://huggingface.co/Qwen/Qwen3.5-4B (config checked 2026-11-14).
- `Qwen3_5ForConditionalGeneration`, 32 layers, hidden 2560, tied embeddings, includes a vision tower.
- **Hybrid attention:** a repeating block of 3 linear-attention (Gated-DeltaNet-style) layers + 1 full-attention layer (`full_attention_interval: 4`). Residual-stream probes and steering work as usual. Attention-pattern tools and TransformerLens may not support it.
- Same family as the paper's RL model (Qwen3.5-9B) and the HF RL checkpoints:
  - https://huggingface.co/context-language-model/rl-ckpt-b0sum_dapo-iter49: Qwen3.5-9B-Base fine-tune, probably the summary-harness arm.
  - https://huggingface.co/context-language-model/rl-ckpt-livectx_dapo-iter44: probably the CLM arm. Base not stated, and it may be gated.
- Dev model if 4B is too slow: Qwen3.5-2B. Step-up if 4B floors: Qwen3.5-9B.
- Risk: the paper says 9B CLM underperforms the summary harness "due to the smaller model's limited context-management capabilities". 4B may floor. Step 2 below is the gate.

## Step 0: environment

```bash
cd context-language-models
python3.12 -m venv .venv && . .venv/bin/activate
pip install -e .                               # harbor==0.16.1, litellm, tiktoken, pyyaml
git clone https://github.com/RulinShao/ContextBench.git ../ContextBench
pip install -e "../ContextBench[tokenizer]"
```

- Needs Docker (or Singularity) for Harbor sandboxes, and a GPU box for vLLM. **Hardware not decided yet.**
- `.gitignore` currently ignores `external/`, but the repo now sits at `context-language-models/`. Fix before committing.

## Step 1: serve Qwen3.5-4B

Adapted from `clm/clm_harness/README.md` (the paper command is for Qwen3.6-27B):

```bash
vllm serve Qwen/Qwen3.5-4B --served-model-name qwen35-4b --max-model-len 65536 \
  --enable-auto-tool-choice --tool-call-parser qwen3_coder --reasoning-parser qwen3
```

- The context window must hold `context_budget_tokens + max_tokens`: 32768 + 8192 for ContextBench, 28672 + 4096 for BCP.
- **Unverified:**
  - whether `qwen3_coder` and `qwen3` are the right parsers for Qwen3.5;
  - which vLLM version supports `qwen3_5` hybrid attention. Check the model card's serving section first.
- Text-only: the vision tower is unused. Check whether vLLM can skip loading it to save memory.

## Step 2: smoke test (go/no-go for 4B)

```bash
cd ../ContextBench
contextbench package --all --config clm_exp/configs/paper.yaml --out-dir cb_tasks/ --agent-timeout-sec 21600
OPENAI_API_KEY=EMPTY harbor trials start -p cb_tasks/<kv-store, lowest level> -e docker \
  -a clm_contextbench:ClmStream -m openai/qwen35-4b \
  --agent-kwarg api_base=http://localhost:8000/v1
```

Pass if, on 2-3 low-pressure instances per task:
- the model emits `READY_FOR_NEXT_OP` and finishes the stream (`interactive_stream.json` → `terminated_by`);
- tool calls parse (no format-failure loop);
- at levels >1×, the model actually edits the mirror (real edit counter > 0, diffs visible in `context_snapshots/`).

If 4B never edits, or the tool calls break, switch to 9B before spending more compute.

## Step 3: ContextBench reproduction

Task design (paper App. D, Table 3):
- 4 tasks, each graded **from the agent's context only** (answers held in files get no credit).
- Context pressure (total input / 32,768) runs from 0.25× to 24× (Fig 15). Levels below 1× are controls.

Two conditions, because the paper reports two different setups:

| Condition | Paper source | Settings | Paper number to compare |
|---|---|---|---|
| A. `skill=clm` | Fig 2 (GPT-5.4 only, 4 seeds/level, 8 for some) | `ClmStream` `PAPER_KWARGS`: budget 32768, reserve 2048, no step cap, no nudges, no rollback-retry, `max_tokens` 8192 | No Qwen number. Report the 4B curve per task × pressure level. |
| B. `skill=none` | Fig 20 / App. F, start of in-context evolution | Qwen agent: 32,000 budget, 4,096 reserve, 240 turns, run ends on overflow | Qwen3.6-27B dev: Needle 97.6%, Sudoku 45.3%, KV Store 22.3%, Log Triage 0.0%. KV Store test: 38.3% (3 seeds). |

- Condition B's dev/test splits are 102 instances per task. **Unknown:** where the split and its pressure-level mix are defined. Check `ContextBench/clm_exp/`.
- The `PAPER_KWARGS` budget/reserve (32768/2048) differ from the App. F evolution settings (32000/4096). Pass condition B's values explicitly as `--agent-kwarg`.
- Sanity checks:
  - **Below-1× controls ≈ 100%.** Everything fits, so failures here mean a pipeline or model bug, not context management.
  - Accuracy falls with pressure.
  - Needle Retention is near ceiling: 97.6% for 27B, and the instruction labels the needles.
- `skill=clm` is sha-checked against `PAPER_SKILL_SHA16`. Don't edit the skill files.
- Optional calibration: condition B on a 27B subset (for example 20 KV Store dev instances). Within noise of 22.3% means the pipeline is right.

## Step 4: BrowseComp-Plus

Not runnable from the repo alone. Missing:
1. The BCP corpus and search tools. The paper exposes search as in-context skills: top-10 snippets of 512 tokens, reader capped at 8,192 tokens. `clm/clm_harness/utils/skills.py` mounts a skill dir, but no BCP skill ships. BCP paper: https://arxiv.org/abs/2508.06600.
2. A Harbor task wrapper for the 830 questions (`task_template: open_problems`).
3. A judge. The paper uses Qwen3.5-27B at temperature 0 with the BCP grading template; unanswered counts as wrong. A cheaper judge must be stated as a deviation.

The settings conflict, so pick one and log it:

| | `configs/bcp.yaml` | Paper App. E |
|---|---|---|
| Budget | 28672 | 23,560 |
| Steps | 500 (100 and 2000 also used) | 100 turns (editing turns free) |
| Rollback retries | 6 | 6 |
| Edit gate | `shrink` | not stated |

Paper anchors:
- Qwen3.6-27B CLM: 59.4% (32K).
- Qwen3.5-9B CLM before RL: 28.8%, and 42.5% after RL (Table 2, 28K budget, 80 turns).
- Expect 4B below 28.8%.

Suggested order: first a 50-question subset, then the full 830 only if the subset is informative.

Baseline harnesses (Summary, Self-Compact, ACM, RLM, MEM1) are **not in the repo**. Reproducing them is out of scope unless needed for the elicitation contrast.

## Step 5: what to keep for elicitation and interp

Per trial, under `agent/`:
- `context_snapshots/turn-NNNN.json`: the exact context per call. ContextBench grades these.
- `trajectory.ctx.json` (ATIF-CTX) and `trajectory.json`: edits, before/after tokens.
- `clm_stream.json` (skill, sha16, kwargs) and `interactive_stream.json` (ops, `terminated_by`).
- Edit counters from `ContextEnv.step`: real edits, growth, rejections.

Activations: vLLM does not expose them. Replay saved snapshots through HF `transformers` offline and capture residual streams at the edit-decision tokens. This keeps serving and interp decoupled.

## Confounds to log now (they matter for step 2)

- **Harness nudges** (BCP: 25/50/75% + persistent 90%). Edits may follow the nudges rather than uncertainty. ContextBench `PAPER_KWARGS` turns nudges off, which makes it the cleaner elicitation setting.
- **Token-count hints** (`ctx_hint=default`). Paper App. G: models' context-length awareness degrades at long lengths, and hints fix it. Record the hint setting per run.
- **Edit gate** (`fit` vs `shrink`) checks size only, not content.

## Open decisions

1. Hardware: GPU box, cloud, or the Mac only.
2. vLLM version and parsers for Qwen3.5.
3. BCP: build the corpus, search skill and judge, or defer BCP and do ContextBench first. Recommended: ContextBench first.
4. BCP settings: `bcp.yaml` or App. E.
5. Whether to run the 27B calibration subset.
