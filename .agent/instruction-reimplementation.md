# Experiment: reimplement CLM baselines with Qwen3.5-4B

Written: 2026-11-14. Status: planned, nothing run.
Repo: `context-language-models/` (vendored at the project root, commit `fa5e93b`). Paper: `Context Language Models.pdf` (arXiv 2609.37725).

## TL;DR

| Milestone | Experiment | What it tests |
|---|---|---|
| **M1** | Smoke test (KV Store + Sudoku, 0.5×) | Whether Qwen3.5-4B can operate the CLM harness at all: emit valid tool calls, finish the stream, and score ≈100% when everything fits in context. |
| **M2** | ContextBench KV Store (0.5/2/8/24×, 2 seeds, no skill) | How well 4B keeps exact values retrievable as input grows past the context limit, compared with Qwen3.6-27B's 22.3% in the same no-skill setup. |
| **M3** | ContextBench Sudoku (0.5/2/8/24×, 2 seeds, no skill) | How well 4B maintains a constantly changing state through in-place edits under rising pressure, compared with Qwen3.6-27B's 45.3%. |
| **M4** | BCP (50 questions, `bcp.yaml`, 27B judge) | Whether 4B CLM can do real deep research where it decides what to keep from search results, compared with 9B's 28.8% and 27B's 59.4%. |

M1 gates M2-M4: if 4B fails M1, switch to Qwen3.5-9B. M2, M3 and M4 then run in parallel. Together these validate our pipeline and give the 4B baseline. They also produce the edit trajectories for the elicitation experiment.

## Experiment config

Single source of truth for the run. Values marked `# TBD` are open items, and `# check` means verify before running. Agent kwargs are passed as `--agent-kwarg key=value`. ContextBench starts from `ClmStream.PAPER_KWARGS` (`clm/clm_contextbench/clm_stream.py`), and BCP from `clm/clm_harness/configs/bcp.yaml`. Only the overrides listed here differ.

```yaml
experiment: clm-reimplementation-qwen35-4b
date: 2026-11-14

hardware:
  gpu: A40 (48 GB, sm86)
  n_gpus: TBD                       # 1 = shared server; 2+ = ContextBench and BCP on separate servers
  cpu_cores: TBD                    # ~1 core + <1 GB RAM per concurrent trial (66 trials)
  disk_gb: 40

serving:                            # stock vLLM, NO suffix cache reuse
  engine: vllm                      # version: check (needs qwen3_5 hybrid attention on Ampere)
  model: Qwen/Qwen3.5-4B
  served_model_name: qwen35-4b
  dtype: bfloat16                   # A40 has no FP8 tensor cores
  max_model_len: 65536              # must hold budget + max_tokens
  enable_auto_tool_choice: true
  tool_call_parser: qwen3_coder     # check for Qwen3.5
  reasoning_parser: qwen3           # check for Qwen3.5
  api_base: http://localhost:8000/v1
  litellm_model: openai/qwen35-4b
  env: {OPENAI_API_KEY: EMPTY}

contextbench:
  dataset: context-language-model/ContextBench   # 333 MB
  repo: https://github.com/RulinShao/ContextBench
  package: contextbench package --all --config clm_exp/configs/paper.yaml --out-dir cb_tasks/ --agent-timeout-sec 28800
  agent: clm_contextbench:ClmStream
  harbor_env: docker
  tasks: [kv_store, sudoku_sketchpad]
  pressure_levels: [0.5, 2, 8, 24]  # x of 32,768 tokens; pick the nearest generator values in paper.yaml (check)
  seeds: 2                          # -> 2 x 4 x 2 = 16 trials
  agent_timeout_sec: 28800          # paper: 21600; raised for slow 24x trials
  agent_kwargs:                     # overrides on top of PAPER_KWARGS (App. F no-skill setup)
    skill: none                     # no method skill
    context_budget_tokens: 32000    # PAPER_KWARGS: 32768
    context_budget_reserve_tokens: 4096   # PAPER_KWARGS: 2048
    max_steps: 240                  # App. F "240 turns"; check mapping vs lm_call_cap
  inherited_from_PAPER_KWARGS:      # listed for the record, not passed
    lm_call_cap: 0
    max_tokens: 8192                # larger than the 4096 reserve; check App. F used the same
    temperature: 0.7
    top_p: 0.95
    observation_max_chars: 50000
    nudge_ratios: ""                # no nudges
    persistent_nudge_ratio: null
    finalize_nudge_turns: 0
    max_num_retry_on_limit: 0       # run ends at the budget wall
    allow_edit_growth: fit
    ctx_hint: default
    finish_policy: submit
    enable_thinking: true
    send_chat_template_kwargs: true
    cost_metric: usd                # no FLOPs accounting for ContextBench
  metrics:
    kv_store: exact-value accuracy over 24 GETs, graded from context snapshots
    sudoku_sketchpad: fraction of board versions reproduced exactly
  paper_reference: {model: Qwen3.6-27B, setup: no skill, split: dev, kv_store: 22.3, sudoku_sketchpad: 45.3}

bcp:
  corpus: Tevatron/browsecomp-plus-corpus       # 1.76 GB, 100,195 docs
  queries: Tevatron/browsecomp-plus             # 2.78 GB, 830 queries
  n_questions: 50
  sample_seed: 0                    # save the sampled query_ids
  search_skill:                     # to build; the only skill BCP gets
    retriever: bm25
    top_k: 10
    snippet_tokens: 512
    reader_max_tokens: 8192
  agent: clm_harness.clm_agent.harness:ClmAgent
  config: clm/clm_harness/configs/bcp.yaml
  env: {CLM_EDIT_GATE: shrink}
  agent_kwargs:                     # = bcp.yaml, except the cost metric
    max_steps: 500
    max_tokens: 4096
    temperature: 0.7
    top_p: 0.95
    command_timeout: 120
    persistent_bash: true
    observation_max_chars: 60000
    context_budget_tokens: 28672
    context_budget_reserve_tokens: 2048
    nudge_ratios: "0.25,0.5,0.75"
    persistent_nudge_ratio: 0.9
    max_num_retry_on_limit: 6
    retry_edit_margin_tokens: 2048
    finalize_nudge_turns: 3
    ctx_hint: default
    task_template: open_problems
    cost_metric: flops
    flops_n_body: TBD               # 4B non-embedding params; bcp.yaml uses flops_model_key: 27b
  judge:
    model: Qwen/Qwen3.5-27B-GPTQ-Int4   # paper: unquantized Qwen3.5-27B (deviation)
    temperature: 0
    template: BrowseComp-Plus grading template
    rule: correct only if correct and complete; unanswered = wrong
    when: after all agent runs finish
  paper_reference: {qwen36_27b_clm: 59.4, qwen35_9b_clm_before_rl: 28.8}

execution:
  concurrency: all trials at once   # harbor flag: check `harbor jobs start --help`
  order: longest first (24x levels first)
  trials_dir: trials/
  keep_per_trial:
    - agent/context_snapshots/
    - agent/trajectory.json
    - agent/trajectory.ctx.json
    - agent/clm_stream.json
    - agent/interactive_stream.json
    - agent/usage.json
  estimates: {contextbench_wall_h: "1.2-3.6", bcp_wall_h: "0.5-2", total_1xA40_h: "2-5"}
```

## Goal

Get CLM running end-to-end on ContextBench and BrowseComp-Plus (BCP) with a model small enough for mech interp, and confirm the pipeline is correct before the elicitation experiment (step 2 of `query.md`).

"Correct" does not mean matching the paper's numbers. The paper used Qwen3.6-27B, so 4B numbers will be lower. It means:
1. Runs finish and are graded with the paper's settings.
2. The sanity checks in step 3 hold.

## Setup at a glance

| | Choice |
|---|---|
| Agent model | Qwen3.5-4B (BF16, vLLM) |
| Judge (BCP only) | Qwen3.5-27B-GPTQ-Int4 |
| Hardware | A40 (48 GB). Number of GPUs and CPU cores still to confirm. |
| ContextBench | KV Store + Sudoku, `skill=none`, levels 0.5× / 2× / 8× / 24×, 2 seeds = **16 trials** |
| BCP | 50-question fixed random subset, `bcp.yaml` settings |
| Parallelism | All trials run concurrently (one Docker container each), longest first |

## Model: Qwen3.5-4B

- HF: https://huggingface.co/Qwen/Qwen3.5-4B (config checked 2026-11-14).
- `Qwen3_5ForConditionalGeneration`, 32 layers, hidden 2560, tied embeddings, vision tower (unused).
- **Hybrid attention:** a repeating block of 3 linear-attention (Gated-DeltaNet-style) layers + 1 full-attention layer (`full_attention_interval: 4`).
  - Residual-stream probes and steering work as usual.
  - Attention-pattern tools and TransformerLens may not support it.
- Same family as the paper's RL model (Qwen3.5-9B) and the HF RL checkpoints:
  - https://huggingface.co/context-language-model/rl-ckpt-b0sum_dapo-iter49: Qwen3.5-9B-Base fine-tune, probably the summary arm.
  - https://huggingface.co/context-language-model/rl-ckpt-livectx_dapo-iter44: probably the CLM arm. Base not stated, and it may be gated.
- Fallback if 4B floors: Qwen3.5-9B. The paper says even 9B underperforms "due to the smaller model's limited context-management capabilities". Step 2 is the gate.

## Data and disk

| Item | Download |
|---|---|
| https://huggingface.co/datasets/context-language-model/ContextBench | 333 MB |
| https://huggingface.co/datasets/Tevatron/browsecomp-plus-corpus (100,195 docs) | 1.76 GB (3.26 GB unpacked) |
| https://huggingface.co/datasets/Tevatron/browsecomp-plus (830 queries + attached docs) | 2.78 GB |
| Qwen3.5-4B weights | ~9-10 GB (not checked) |
| Qwen3.5-27B-GPTQ-Int4 weights | ~15-20 GB (not checked) |
| BM25 index | a few GB (not checked) |
| Run outputs (mostly `context_snapshots/`) | ~0.5 GB |

Budget **~35-40 GB** of disk.

## Step 0: environment (prerequisite for M1-M4)

```bash
cd context-language-models
python3.12 -m venv .venv && . .venv/bin/activate
pip install -e .                               # harbor==0.16.1, litellm, tiktoken, pyyaml
git clone https://github.com/RulinShao/ContextBench.git ../ContextBench
pip install -e "../ContextBench[tokenizer]"
```

You also need Docker (or Singularity) for the Harbor sandboxes.

## Step 1: serve Qwen3.5-4B (prerequisite for M1-M4)

Adapted from `clm/clm_harness/README.md`; the paper's command is for Qwen3.6-27B:

```bash
vllm serve Qwen/Qwen3.5-4B --served-model-name qwen35-4b --max-model-len 65536 \
  --enable-auto-tool-choice --tool-call-parser qwen3_coder --reasoning-parser qwen3
```

- The context window must hold `context_budget_tokens + max_tokens`: 32000 + 8192 for ContextBench, 28672 + 4096 for BCP.
- **Unverified:**
  - whether the parsers are right for Qwen3.5;
  - which vLLM version supports `qwen3_5` hybrid attention on Ampere (A40 = sm86). Check the model card's serving section.
- BF16 only. The A40 has no FP8 tensor cores.

## Step 2 — M1: smoke test (go/no-go for 4B)

```bash
cd ../ContextBench
contextbench package --all --config clm_exp/configs/paper.yaml --out-dir cb_tasks/ --agent-timeout-sec 28800
OPENAI_API_KEY=EMPTY harbor trials start -p cb_tasks/<kv-store, 0.5x level> -e docker \
  -a clm_contextbench:ClmStream -m openai/qwen35-4b \
  --agent-kwarg api_base=http://localhost:8000/v1 --agent-kwarg skill=none
```

Run on KV Store and Sudoku, lowest level, about 30 min. Pass if:
- the model emits `READY_FOR_NEXT_OP` and finishes the stream (`interactive_stream.json` → `terminated_by`);
- tool calls parse (no format-failure loop);
- the controls score ≈ 100%.

Then run one 2× trial and check that the model actually edits the mirror (real edit counter > 0, diffs in `context_snapshots/`).

**Measure tokens per call here.** It decides whether the time estimates below sit at the low end (~1k tokens) or the high end (~3k). If 4B never edits, or the tool calls break, switch to 9B.

## Step 3 — M2 (KV Store) + M3 (Sudoku): ContextBench

Settings: **`skill=none`** with the App. F agent settings, which give the paper's only Qwen comparison:
- `--agent-kwarg skill=none --agent-kwarg context_budget_tokens=32000 --agent-kwarg context_budget_reserve_tokens=4096`;
- a 240-turn cap; the run ends on overflow;
- no skill evolution;
- `--agent-timeout-sec 28800` (raised from the paper's 21600 so slow 24× trials are not cut off).

Check in `clm_stream.py` how the 240-turn cap maps to `max_steps`/`lm_call_cap`.

Tasks (paper App. D, Table 3), graded **from the agent's context only**:

| Task | Input | Metric | Graded items |
|---|---|---|---|
| KV Store | batches of 100 SET ops, random 24-word values | exact-value accuracy on 24 GETs | 24 per trial → 192 total |
| Sudoku Sketchpad | one move per turn, 16×16 board | board versions reproduced exactly | ~1 per move → ~580 total |

Design: 2 tasks × levels **0.5× (control), 2×, 8×, 24×** × 2 seeds = **16 trials**.
- Pressure = total input / 32,768 (Fig 15).
- The level-to-pressure mapping was read off a garbled PDF extraction. Confirm the generator values in `clm_exp/configs/paper.yaml` and pick the nearest levels.
- About 4.5M input tokens pushed in total.

Paper comparison: Qwen3.6-27B, no skill, dev split: **KV Store 22.3%, Sudoku 45.3%** (App. F).
- The dev split's level mix is unknown, so the comparison is loose. Expect 4B lower.
- Also report accuracy against pressure.

Sanity checks:
- **0.5× controls ≈ 100%.** Everything fits, so failures here are pipeline or model bugs.
- Accuracy falls with pressure.

Statistics: 2 independent runs per task × level. This detects trends, not differences under about 10-15 points.

## Step 4 — M4: BrowseComp-Plus (50-question subset)

Not runnable from the repo alone. To build:
1. **Search tools as a skill.** Use a BM25 index over the corpus: top-10 snippets of 512 tokens, document reader capped at 8,192 tokens. Mount it with `clm/clm_harness/utils/skills.py`. This is the only skill BCP gets; it's needed to search at all. BCP paper: https://arxiv.org/abs/2508.06600.
2. **A Harbor task wrapper** for the 50 sampled questions (`task_template: open_problems`). Fix the sampling seed and save the question IDs.
3. **Judge:** Qwen3.5-27B-GPTQ-Int4 (https://huggingface.co/Qwen/Qwen3.5-27B-GPTQ-Int4) at temperature 0 with the BCP grading template. Correct only if "correct and complete"; unanswered counts as wrong. The paper uses unquantized 27B; state this as a deviation. Run the judge after the agent runs finish.

Settings: `configs/bcp.yaml` (decided). Log that it differs from paper App. E:

| | `configs/bcp.yaml` | Paper App. E |
|---|---|---|
| Budget | 28672 | 23,560 |
| Steps | 500 | 100 turns (editing turns free) |
| Rollback retries | 6 | 6 |
| Edit gate | `shrink` | not stated |
| Nudges | 25/50/75% + persistent 90% | same harness |

Paper anchors: Qwen3.6-27B CLM 59.4%; Qwen3.5-9B CLM 28.8% before RL. Expect 4B below 28.8%.

Use `cost_metric=flops` with `flops_n_body=<4B non-embedding params>`; only the `9b` and `27b` keys exist. The FLOPs formula may not model linear-attention layers (unverified), so treat cost as approximate. Use `cost_metric=usd` to skip FLOPs entirely.

Baseline harnesses (Summary, Self-Compact, ACM, RLM, MEM1) are **not in the repo** and are out of scope.

## Step 5: parallelism, time, cost

- **CPU:** every trial runs in its own Docker container, about 1 core and under 1 GB RAM each. Run all trials at once: 16 ContextBench + 50 BCP ≈ 66 containers.
  - Check Harbor's concurrency flag with `harbor jobs start --help`.
  - BCP retrieval runs on the CPU and could become the bottleneck at 50 concurrent questions.
- **Order:** launch the 24× trials first.
- **GPU:** with 2+ A40s, run ContextBench and BCP on separate vLLM servers.
- **The limit is the longest trial,** not total work. LM calls inside a trial are sequential, so parallelism can't go below it.

| Run | LM calls | Generated tokens | GPU work | Wall clock (critical path) |
|---|---|---|---|---|
| Smoke test | ~100 | <0.3M | minutes | ~30 min |
| ContextBench, 16 trials | ~1,700 | 1.7-5M | ~25-70 min | **~1.2-3.6 h**, one 24× trial is ~280 sequential calls at ~65 tok/s |
| BCP, 50 questions | ~2-3k | 2-8M | ~0.5-2 h | ~0.5-2 h |
| Judge, 50 answers | 50 | small | minutes | minutes |

- Total on 1 A40: about 2-5 h. On 2 A40s running in parallel: about 1.2-3.6 h.
- Cost is about 1 A40-hour per wall-clock hour. Roughly $1-4 on rented hardware, assuming $0.40-0.80/h (not checked; use your provider's rate).
- All of these are estimates until step 2 measures tokens per call.

## Step 6: what to keep for elicitation and interp

Per trial, under `agent/`:
- `context_snapshots/turn-NNNN.json`: the exact context per call. ContextBench grades these.
- `trajectory.ctx.json` (ATIF-CTX) and `trajectory.json`: edits, with before/after token counts.
- `clm_stream.json` (skill, kwargs) and `interactive_stream.json` (ops, `terminated_by`).
- Edit counters from `ContextEnv.step`: real edits, growth, rejections.
- Count the **edit events** per trial. They are the unit of the elicitation dataset.

Activations: vLLM does not expose them. Replay the saved snapshots through HF `transformers` offline and capture residual streams at the edit-decision tokens.

## Confounds to log now

- **Harness nudges:**
  - BCP fires them at 25/50/75% plus a persistent 90%, so edits may follow the nudges rather than uncertainty.
  - ContextBench `PAPER_KWARGS` turns nudges off, which makes it the cleaner elicitation setting.
- **Token-count hints** (`ctx_hint=default`): paper App. G finds context-length awareness degrades at long lengths and hints fix it. Record the setting per run.
- **Edit gate** (`fit` vs `shrink`): checks size only, not content.

## Open items

1. Number of A40s and CPU cores.
2. vLLM version and parsers for Qwen3.5 on Ampere.
3. Exact ContextBench levels nearest 0.5× / 2× / 8× / 24× in `paper.yaml`.
4. Exact Harbor concurrency flag.
