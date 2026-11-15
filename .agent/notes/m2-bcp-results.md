# M2 BCP results: BrowseComp-Plus (deep research), Qwen3.5-4B vs 9B (combined)

Date: 2026-11-14, 18:23–22:24 UTC. Status: **done**.
Plan: [`../instruction-reimplementation.md`](../instruction-reimplementation.md) (M4).
ContextBench (M2) results: [`m2-contextbench-results.md`](m2-contextbench-results.md).
This file holds the full content of the three BCP per-run notes (originals kept in [`archive/`](archive/), listed at the end),
plus the per-question evaluation table from `figs/`. Raw trials live under `runs/` (gitignored).

## Headline

| | 4B | 9B |
|---|---|---|
| 50 q, correct after hand check | 10 / 50 (20%) | **13 / 50** (26%) |
| trials with ≥ 1 context edit | 19 (38%) | 35 (70%) |
| correct when edited / not | 47% vs 3% | 31% vs 7% |

On 50 questions, with our own method text, the 9B is slightly ahead: 13 vs 10 correct
after a hand check. In both models, trials that edited their context were far more often correct.
Without a method text (smoke v1) the 4B answered 0/5: it never offloads search results.

## Setup (control unless marked)

- Agent: `ClmAgent` with [`bcp.yaml`](../../context-language-models/clm/clm_harness/configs/bcp.yaml):
  max_steps 500, T=0.7, budget 28672 / reserve 2048, nudges 0.25 / 0.5 / 0.75 + persistent 0.9,
  finalize nudges 3.
- **Changed vs bcp.yaml:** `cost_metric=usd` (bcp.yaml's FLOPs key is for 27B; 4B `flops_n_body` not set).
- Model server: shared with ContextBench runs (`infra/serve_qwen35_4b.sh` for the 4B).
- Retrieval: search skill `infra/bcp/skill/bcp_search` (BM25, top-10, 512-token snippets, 8192-token
  reader; plan settings), server on :8100. Sandbox: proot (`infra/chroot_env.py`); :8100 reachable from proot (checked).
- Questions: the fixed 50-question sample (`data/bcp/sample_seed0_n50.json`, seed 0); smoke used
  5 of them (624, 1204, 679, 69, 427). One run per question.
- Grading: substring match of the gold answer in `Exact Answer:`, plus a hand check. **No LLM
  judge** (user decision 2026-11-14: skip the judge this sprint); answers are kept in `/app/answer.md` for later judging.
- Instruction and SKILL.md are our own wording (deviation; paper's BCP prompt not in repo).

## 1. Smoke v1: as configured (4B, 5 questions)

18:23–18:30 UTC (all 5 trials finished in 17 s to 7.4 min), concurrently with M2 KV. Raw trials: `runs/bcp-smoke/trials/`.

| QID | reward (substring) | answered | steps / LM calls | edits | peak ctx | terminated |
|---|---|---|---|---|---|---|
| 427 | 0 | no | 1 / 1 | 0 | 2.1k | gave up: submitted on the first call without searching |
| 624 | 0 | no | 22 LM calls, 12 kept | 0 | ~28k (budget) | budget exhausted after 6/6 rollbacks (3 min) |
| 1204 | 0 | no | 20 LM calls, 9 kept | 0 | ~27k (budget) | budget exhausted after 6/6 rollbacks (5 min) |
| 679 | 0 | no | 52 LM calls, 12 kept | 1 real, 1 rejected | ~29k (budget) | budget exhausted after 6/6 rollbacks (7.4 min) |
| 69 | 0 | no | 22 LM calls, 13 kept in trajectory | 0 | 28.6k (budget) | budget exhausted after 6/6 rollbacks; ignored the final-turn notice (searched again) |

Observations:

- 427: the model reasoned the question was too hard and ran
  `echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT` immediately. Model behavior, not a pipeline bug.
- Harmless proot warning in every command: host cwd absent in guest, falls back to `/`.
- 69 hit the context limit early and rolled back (`rollback_retry`), so budget handling is active.
- 69 (finished 18:25, 2.5 min): **no context edits at all** (`n_ctx_syncs_real 0`) despite 3 nudges.
  Each `search` returns ~10 x 512-token snippets (~4-5k tokens), so the 28.6k budget holds
  only ~4-5 searches. The model kept issuing ever-shorter keyword searches (`search "ugly"`,
  `search "trolled"`), hit the limit, was rolled back 6 times, then on the FINAL-turn notice
  searched again instead of writing `/app/answer.md`. Same pattern as M1 `skill=none`:
  without a method text, 4B does not offload; BCP gets only the search skill.
- 624: same failure as 69. 0 edits, 3 nudges ignored, one `get_document`, then single-word
  searches (`search "coffee"`, `search 'Colombia'`) until 6/6 rollbacks. Ended without an answer.
- 1204: same failure. 0 edits, 8 nudges ignored. Searches were on target (identified the
  topic as Zelda / Ocarina of Time, was narrowing to Link's voice actor) but it never wrote
  a provisional answer before the budget ran out. Best candidate for a fix: it was close.
- 679: the only trial that touched its context: one Python edit of `LIVE_CTX_MAIN.txt`
  (1 accepted, 1 rejected), then back to searching (Purdue / Murphy award / Crossley) until
  6/6 rollbacks. 9 nudges. No answer.

Summary: **0/5 answered, 0/5 correct.** The pipeline works end to end (search server reachable
from proot, `search` / `get_document` called correctly, nudges and rollbacks fire,
verifier writes `reward.json`). The model is the bottleneck:

1. **No offloading.** 4 of 5 trials made 0 context edits; 679 made 1. Same as M1 with
   `skill=none`: 4B does not edit context without a method text, and BCP gets only the
   search skill. Compare KV, where `skill=clm` gives 1 edit per batch and 24/24 at R1000.
2. **Search results flood the budget.** ~4-5k tokens per `search` (10 x 512-token snippets)
   vs a 28.6k budget: ~5 searches before the wall. Rollbacks then loop the model.
3. **No answer under pressure.** None wrote a provisional `/app/answer.md`, even on the
   FINAL-turn notice (69 searched again). 427 quit at call 1.
4. Query quality degrades into single keywords (`search "ugly"`, `search 'Colombia'`).
   1204 was on the right track (Zelda / Ocarina of Time) when the budget ran out.

Implication for M4 at the time: as configured, expect ~0%. Options considered: (a) a BCP method
text (offload search results to a notes file, keep a running candidate answer), our addition, not
the paper's; (b) `k=3-5` / shorter snippets, deviating from the plan's top-10 x 512; (c) instruct
"write a provisional answer early"; (d) run as-is and report 4B as below floor. Chosen: (a)+(c), below.

## 2. Smoke v2 / v3: our BCP method text (4B, same 5 questions, 18:48–19:01 UTC)

Our addition, **not the paper's setup**: the paper's BCP runs give no method text. Same 5
questions, same `bcp.yaml` settings, same substring grader.

- Tools now wrap every output in `<<<R0007 BEGIN ... R0007 END>>>` (unique anchor per result).
- Method text ([`infra/bcp/skill/bcp_search_clm/SKILL.md`](../../infra/bcp/skill/bcp_search_clm/SKILL.md)),
  modelled on the paper's KV recipe: one `python3` heredoc per result that writes a one-line
  note to `/app/notes.md`, moves the block to `/tmp/ctx_offload/`, replaces it with the note,
  `&& search` next. Plus: write a provisional `/app/answer.md` as soon as there is a candidate.
- **v2**: method text in the skill's SKILL.md (system prompt). `BCP_SKILL=bcp_search_clm`.
- **v3**: same method text inserted into the task instruction before `## Output`, as
  ContextBench places its method section; skill = tools only. `BCP_SKILL=bcp_search_ids
  BCP_TASKS=bcp_tasks_v3` (built by [`infra/bcp/make_v3_tasks.py`](../../infra/bcp/make_v3_tasks.py)).

| QID | v1 (as configured) | v2 (method in system prompt) | v3 (method in instruction) |
|---|---|---|---|
| 69 | 0, no answer, 0 edits | **1** (Chikwe), 4 edits, 36 calls | **1** (Chikwe), 1 edit, 12 calls |
| 624 | 0, no answer, 0 edits | 0, answered wrong (conf 100%), 1 edit | **1**, answered |
| 427 | 0, quit at call 1 | 0, no answer, 0 edits | 0, no answer, 3 edits |
| 679 | 0, no answer, 1 edit | 0, no answer, 1 edit | 0, quit at call 1 |
| 1204 | 0, no answer, 0 edits | 0, no answer, 0 edits | 0, no answer, 0 edits |
| **answered / correct** | 0 / 0 | 2 / 1 | **2 / 2** |

- The method text moves BCP off zero, but adoption is weak: most trials still make 0–1
  edits, far from KV's one-edit-per-batch. Successes came from batching: v3 69 offloaded
  four result blocks in one edit, then answered from `/tmp/ctx_offload`.
- Placement matters a little (v3 ≥ v2 here), consistent with ContextBench putting the
  method in the instruction. n = 5, so this is a direction, not a result.
- Remaining failure modes: quitting at call 1 (427, 679), ignoring the recipe and
  searching until the wall (1204 in all three variants), and confident wrong answers.
- Decision (rule set before the run: ≥ 2/5 answered → run 50): **run the 50-question
  sample with v3**. The 5 smoke tasks were rebuilt for the 50 run; the instruction differs
  from the smoke v3 copy by one blank line.

## 3. 50 questions, v3: 4B and 9B

4B: 19:02–19:37 UTC (35 min, 8 concurrent, `runs/bcp50-v3/`), sharing the server with LogTriage / Needle.
9B: 21:04–22:24 UTC (80 min, 10 concurrent, `runs/bcp50-v3-9b/`, `MODEL=qwen35-9b`), mostly alone on the
9B server (the last 9B ContextBench trials finished during the first 20 min). Setup identical otherwise.

![BCP 4B](figs/bcp50-v3.png)
![BCP 9B](figs/bcp50-v3-9b.png)

| | 4B | 9B |
|---|---|---|
| correct (substring, strict) | 10 / 50 | **12 / 50** |
| correct after hand check | 10 | **13** (+ 1 possible alias) |
| answered | 12 | 21 |
| wrong answers | 2 | 9 |
| no answer, budget exhausted (6/6 rollbacks) | 33 | 29 |
| no answer, quit within 2 calls | 5 | 0 |
| trials with ≥ 1 context edit | 19 (38%) | 35 (70%) |
| correct when edited / not | 9 / 19 vs 1 / 31 | 11 / 35 vs 1 / 15 |
| mean LM calls / minutes per question | 13.7 / 5.3 | 23.7 / 12.0 |
| run | 19:02–19:37, 8 concurrent | 21:04–22:24, 10 concurrent |

4B outcome by whether the trial edited its context:

| outcome | made ≥ 1 context edit (n=19) | no context edit (n=31) | total |
|---|---|---|---|
| correct | **9** | 1 | 10 |
| wrong answer | 0 | 2 | 2 |
| no answer, budget exhausted (6/6 rollbacks) | 10 | 23 | 33 |
| no answer, quit within 2 calls | 0 | 5 | 5 |

Hand check: all 10 4B "correct" are exact gold matches (no false positives) and its 2 wrong answers
are genuinely wrong. Of the 9B's 9 "wrong": **1252** "2004 Athens Olympics (Aug 13-29, 2004)" vs gold
"August 13-August 29, 2004" is equivalent (substring false negative, counted correct); **987** "Guillem
Vilella Falgueras" vs gold "Guille Milkyway" may be the same person under a stage name (not verifiable
offline, counted wrong); the other 7 are wrong (e.g. 624: 66% vs 65%).

Paper references (plan; judged, paper's own setup, no method text): Qwen3.5-9B 28.8%, Qwen3.6-27B 59.4%.
Our 4B: 20%; our 9B: 24–26%. Close for the 9B, but not the same condition (our method text, substring grader).

### Per-question evaluation (50 questions, both models)

Outcome is the strict substring grade; see the hand check above for 1252 and 987.

| QID | Gold | 4B outcome | 4B answer (conf) | 4B calls / edits / nudges / min | 9B outcome | 9B answer (conf) | 9B calls / edits / nudges / min |
|---|---|---|---|---|---|---|---|
| 69 | Chikwe | no answer (budget) | – | 13 / 0 / 3 / 5.4 | **correct** | Chikwe (100%) | 12 / 2 / 4 / 8.3 |
| 100 | Phoenix New Times | no answer (budget) | – | 12 / 0 / 2 / 2.4 | no answer (budget) | – | 12 / 0 / 2 / 2.5 |
| 120 | Why would any graduate want to start a business in Nigeria? | **correct** | Why would any graduate want to start a business in Nigeria? (100%) | 14 / 3 / 4 / 5.3 | **correct** | Why would any graduate want to start a business in Nigeria? (95%) | 18 / 1 / 4 / 5.7 |
| 161 | Kune Rima | no answer (budget) | – | 12 / 0 / 2 / 3.5 | no answer (budget) | – | 12 / 1 / 2 / 3.2 |
| 169 | Immaterial | no answer (quit) | – | 1 / 0 / 0 / 0.7 | no answer (budget) | – | 12 / 0 / 2 / 6.0 |
| 171 | June 2023 | no answer (budget) | – | 13 / 0 / 3 / 3.5 | no answer (budget) | – | 12 / 0 / 2 / 3.5 |
| 235 | Osama Heikal | no answer (budget) | – | 12 / 0 / 3 / 5.3 | **correct** | Osama Heikal (95%) | 22 / 16 / 2 / 17.6 |
| 236 | June | no answer (budget) | – | 13 / 0 / 3 / 3.4 | no answer (budget) | – | 12 / 0 / 3 / 5.8 |
| 244 | Psychedelics | no answer (budget) | – | 25 / 6 / 10 / 11.4 | no answer (budget) | – | 32 / 4 / 14 / 9.0 |
| 330 | The Last of Us | wrong answer | Stranger Things (75%) | 12 / 0 / 2 / 4.2 | no answer (budget) | – | 12 / 0 / 2 / 3.2 |
| 362 | Captain Star | no answer (budget) | – | 12 / 0 / 2 / 2.9 | no answer (budget) | – | 12 / 0 / 2 / 3.4 |
| 416 | Hsiang Sing Naik | no answer (budget) | – | 12 / 0 / 2 / 2.6 | no answer (budget) | – | 21 / 3 / 8 / 7.8 |
| 427 | Guerlain | no answer (budget) | – | 12 / 0 / 2 / 4.4 | wrong answer | Singer Company (40%) | 40 / 9 / 19 / 35.8 |
| 428 | Preston | no answer (budget) | – | 14 / 0 / 3 / 5.0 | **correct** | Preston (95%) | 12 / 0 / 2 / 4.4 |
| 473 | 28 October 2014 | no answer (quit) | – | 1 / 0 / 0 / 0.4 | no answer (budget) | – | 16 / 2 / 5 / 5.4 |
| 505 | Max Mazanov | **correct** | Max Mazanov (100%) | 27 / 9 / 6 / 17.3 | **correct** | Max Mazanov (100%) | 29 / 5 / 14 / 16.7 |
| 514 | Maximilian Josef Sommer | **correct** | Maximilian Josef Sommer (100%) | 14 / 1 / 6 / 6.6 | **correct** | Maximilian Josef Sommer (100%) | 16 / 2 / 5 / 6.3 |
| 521 | Chop Sock Chooks Bang Bang Bang Bang | no answer (budget) | – | 14 / 1 / 3 / 6.6 | no answer (budget) | – | 12 / 0 / 2 / 4.2 |
| 540 | Casey Means | no answer (budget) | – | 14 / 0 / 3 / 2.3 | no answer (budget) | – | 13 / 0 / 3 / 3.1 |
| 576 | Cobra Verde | no answer (quit) | – | 1 / 0 / 0 / 0.4 | wrong answer | The Name of the Rose (60%) | 21 / 5 / 7 / 11.2 |
| 581 | 90g | **correct** | 90g (95%) | 29 / 2 / 7 / 9.8 | no answer (budget) | – | 64 / 16 / 28 / 53.6 |
| 624 | 65% | no answer (budget) | – | 13 / 1 / 3 / 4.4 | wrong answer | 66% (95%) | 25 / 6 / 6 / 16.9 |
| 652 | Auxly | no answer (budget) | – | 21 / 2 / 5 / 9.2 | no answer (budget) | – | 21 / 5 / 7 / 9.1 |
| 679 | ASCENT project 10 | no answer (budget) | – | 13 / 1 / 3 / 5.8 | wrong answer | Aircraft Technology Modeling and Assessment (95%) | 29 / 5 / 14 / 14.1 |
| 702 | Robert D. McBain | no answer (budget) | – | 12 / 0 / 2 / 3.4 | no answer (budget) | – | 18 / 2 / 6 / 7.4 |
| 713 | Kai Tomety | no answer (budget) | – | 14 / 0 / 3 / 6.6 | wrong answer | Unable to determine from available search results (0%) | 22 / 2 / 10 / 8.7 |
| 751 | Alan Sanfey | no answer (budget) | – | 12 / 0 / 2 / 4.3 | no answer (budget) | – | 12 / 0 / 2 / 5.1 |
| 758 | Pipe | no answer (budget) | – | 13 / 0 / 3 / 4.7 | wrong answer | Dual Haloes (chakrams) (75%) | 21 / 4 / 8 / 12.3 |
| 771 | Vakkorama | **correct** | Vakkorama (100%) | 18 / 4 / 7 / 10.1 | **correct** | Vakkorama (100%) | 10 / 1 / 3 / 6.6 |
| 796 | Odeal | no answer (quit) | – | 1 / 0 / 0 / 0.5 | no answer (budget) | – | 12 / 0 / 3 / 7.8 |
| 805 | Ana Djaimilia dos Santos Pereira de Almeida Brito | no answer (budget) | – | 28 / 6 / 11 / 16.3 | no answer (budget) | – | 49 / 10 / 19 / 45.7 |
| 821 | 94% | no answer (budget) | – | 12 / 0 / 2 / 2.6 | **correct** | 94% (80%) | 103 / 24 / 47 / 32.0 |
| 838 | Sandie Hatch | no answer (budget) | – | 17 / 1 / 6 / 3.4 | no answer (budget) | – | 21 / 5 / 7 / 7.1 |
| 869 | kindergarten | no answer (budget) | – | 12 / 0 / 2 / 2.9 | no answer (budget) | – | 18 / 2 / 5 / 4.5 |
| 873 | 27 | no answer (budget) | – | 12 / 0 / 3 / 3.3 | no answer (budget) | – | 56 / 20 / 24 / 18.7 |
| 887 | Javier Rodriguez | **correct** | Javier Rodriguez (95%) | 18 / 0 / 3 / 4.9 | no answer (budget) | – | 12 / 0 / 2 / 3.5 |
| 927 | Plastic Man | no answer (budget) | – | 12 / 0 / 2 / 3.2 | no answer (budget) | – | 14 / 1 / 3 / 5.4 |
| 962 | Spatial Analysis of Weather Crash Patterns | no answer (budget) | – | 19 / 4 / 5 / 12.4 | no answer (budget) | – | 26 / 7 / 7 / 13.0 |
| 978 | Olka Gretcher | **correct** | Olka Gretcher (100%) | 17 / 3 / 5 / 6.8 | no answer (budget) | – | 14 / 0 / 5 / 7.3 |
| 987 | Guille Milkyway | no answer (quit) | – | 1 / 0 / 0 / 0.4 | wrong answer | Guillem Vilella Falgueras (85%) | 23 / 5 / 8 / 9.9 |
| 1023 | Hatpin | no answer (budget) | – | 14 / 0 / 4 / 5.6 | **correct** | hatpin (100%) | 33 / 5 / 12 / 12.9 |
| 1082 | Jagannatha Hora | wrong answer | Not found in corpus; possible candidates include Nick Montfo (15%) | 12 / 0 / 2 / 3.0 | no answer (budget) | – | 32 / 7 / 15 / 23.4 |
| 1115 | Norman Vanua | no answer (budget) | – | 25 / 4 / 8 / 13.0 | **correct** | Norman Vanua (100%) | 38 / 19 / 12 / 26.2 |
| 1155 | Giusewa | **correct** | Giusewa (95%) | 12 / 5 / 1 / 5.5 | wrong answer | El Morro National Monument (65%) | 27 / 5 / 10 / 16.9 |
| 1200 | Law & Order: Justice Is Served | no answer (budget) | – | 12 / 0 / 2 / 3.6 | no answer (budget) | – | 12 / 0 / 2 / 3.4 |
| 1204 | Stephan Weyte | **correct** | Stephan Weyte (100%) | 18 / 7 / 3 / 10.3 | no answer (budget) | – | 12 / 0 / 2 / 4.9 |
| 1232 | Prince of Shadows | no answer (budget) | – | 12 / 0 / 2 / 3.6 | no answer (budget) | – | 15 / 3 / 3 / 7.1 |
| 1252 | August 13-August 29, 2004 | no answer (budget) | – | 12 / 0 / 3 / 4.8 | wrong answer | 2004 Athens Olympics (Aug 13-29, 2004, Year: 2004) (60%) | 79 / 23 / 38 / 41.0 |
| 1260 | Aynabaji | no answer (budget) | – | 15 / 1 / 3 / 3.7 | **correct** | Aynabaji (100%) | 11 / 2 / 6 / 7.0 |
| 1266 | Maryam Tanveer Ali | **correct** | Maryam Tanveer Ali (100%) | 10 / 3 / 4 / 4.0 | **correct** | Maryam Tanveer Ali (95%) | 9 / 1 / 5 / 3.3 |

### Analysis: 4B

1. **Editing context is what separates success from failure.** Trials that made at least one
   real context edit got 9/19 right (47%); trials that never edited got 1/31 (3%). This is
   correlation, not proof (easier questions may both invite edits and be solvable), but it
   mirrors ContextBench, where edit-or-not decides the score.
2. **The method text is adopted only 38% of the time** (19/50 trials made any edit). When it
   is adopted it is used sparingly: 1–9 edits, median 3, often batching several blocks into one.
   On KV the same model edits once per batch, every batch.
3. **The "keep a provisional answer" instruction mostly fails.** 33 trials ran out of context
   without writing any answer, despite the instruction, 2–11 nudges each, and the final-turn notice.
   This is the largest loss bucket and the cheapest to fix (e.g. a harness-side finalize turn).
4. **Precision is high:** 10 of 12 answers are right; answers are written only when the
   model has found the evidence. Stated confidence is mostly 95–100%.
5. **Run-to-run variance is large:** 1204 failed in all three smoke variants but is correct
   here, while 69 and 624 (both correct in smoke v3, same setup) ran out of budget unanswered
   here. Smoke v3 on the same 5 questions: 2/5; here: 1/5. n=1 per question, so per-question
   claims are weak, and the 20% has a wide interval (Wilson 95%: ~11–33%).

### Analysis: 9B vs 4B

1. **9B ≥ 4B on BCP, unlike KV / LogTriage.** 12–13 vs 10 correct; the 9B adopts the
   method text far more (70% of trials edit vs 38%), never quits early, and answers 21
   questions vs 12.
2. **Editing still separates success from failure** for both models: 11/35 vs 1/15 (9B, 31% vs 7%),
   9/19 vs 1/31 (4B, 47% vs 3%). Correlational, as before.
3. **The 9B trades precision for coverage:** 12–13 of 21 answers right (≈ 60%) vs 10 of 12
   (83%) for the 4B; it commits to plausible wrong candidates (427, 576, 758).
4. **Budget exhaustion without an answer is still the biggest bucket** (33 / 29 of 50), despite
   the "keep a provisional answer" instruction, for both models.
5. **Cost:** the 9B takes ~1.7x the LM calls and ~2.3x the wall time per question.
6. **Little overlap between the models.** Correct for both: 5 (120, 505, 514, 771, 1266);
   4B only: 5 (581, 887, 978, 1155, 1204); 9B only: 7 (69, 235, 428, 821, 1023, 1115, 1260).
   17 distinct questions solved by at least one model; with n=1 per question, which
   questions get solved is largely run-to-run luck.
7. Wide intervals: Wilson 95% ~11–33% for 10/50, ~16–40% for 13/50.

### Utilization

4B run (19:02–19:42, 30 s samples): GPU util 100% throughout, CPU mean 12% (max 18%) of 96 cores.
GPU-bound, shared with 6–9 ContextBench trials at the same time, so wall-clock times include queueing in vLLM.

## Caveats

- Our method text is a deviation, so the 20–26% is "model + our BCP recipe", not the paper's
  condition.
- Substring grading plus a hand check; the planned 27B judge was not run.
- One run per question; wide intervals (Wilson 95% ~11–33% for 10/50, ~16–40% for 13/50).

## Source notes (archived originals)

| Run | Note | Per-question table |
|---|---|---|
| BCP smoke + v2 / v3 | [`bcp-smoke-results.md`](archive/bcp-smoke-results.md) | (in the note) |
| BCP 50 q, 4B | [`bcp50-v3-results.md`](archive/bcp50-v3-results.md) | [`figs/bcp50-v3.md`](figs/bcp50-v3.md) |
| BCP 50 q, 9B | [`bcp50-v3-9b-results.md`](archive/bcp50-v3-9b-results.md) | [`figs/bcp50-v3-9b.md`](figs/bcp50-v3-9b.md) |
