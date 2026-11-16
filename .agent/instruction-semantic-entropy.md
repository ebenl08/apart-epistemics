# Plan: M6 semantic entropy of CLM context decisions → accuracy → linear probe

Date: 2026-11-15. Runs alongside / after M5 ([`instruction-seed-sweep.md`](instruction-seed-sweep.md)).
Pathway step 2 of [`query.md`](query.md). This file merges the earlier plan and the build
plan (`instruction-se-collection.md`, now removed).

Contents: [Hypothesis](#hypothesis) · [References](#key-references) ·
[Part 0 Background](#part-0-background-and-definitions) ·
[Part 1 Collection, step by step](#part-1-collecting-semantic-entropy-step-by-step) ·
[Part 2 Correlation](#part-2-correlation-analysis-h1) · [Part 3 Probe](#part-3-linear-probe-h2-only-on-go) ·
[Config](#experiment-config-m6) · [Risks](#risks) · [Milestones](#milestones)

## Hypothesis

- **H1 (correlation):** trials where the CLM is more uncertain about its context decisions
  (stay / edit / offload / delete) score lower on ContextBench, beyond what context pressure
  alone explains.
- **H2 (decodability, only if H1 holds):** that uncertainty is linearly decodable from the
  residual stream at the decision point.
- **H3 (later, causal, not in this plan):** steering along the decoded direction raises or
  lowers accuracy against the unsteered baseline.

## Key references

- Kuhn, Gal, Farquhar, ICLR 2023, *Semantic Uncertainty* — [arXiv 2302.09664](https://arxiv.org/abs/2302.09664).
  Entropy over meaning clusters of sampled outputs (bidirectional-entailment clustering).
- Farquhar et al., Nature 2024, *Detecting hallucinations with semantic entropy* —
  [PMC11186750](https://pmc.ncbi.nlm.nih.gov/articles/PMC11186750). Adds **discrete SE**
  (cluster frequencies, no logprobs needed); 10 samples per input.
- Kossen et al. 2024, *Semantic Entropy Probes* — [arXiv 2406.15927](https://arxiv.org/abs/2406.15927).
  Linear probes on hidden states predict SE. Positions: TBG (last input token) and SLT (last
  response token). Target binarized at the threshold γ* minimizing within-group squared error.
  Template for Part 3.
- SE is a **total** uncertainty estimate (it does not split aleatoric / epistemic). That is
  what we report; decomposition is out of scope.

---

## Part 0. Background and definitions

### How one CLM trial runs

```
   ┌──────────────┐  (1) messages = the whole context  ┌───────────┐
   │   HARNESS    │ ──────────────────────────────────▶ │   MODEL   │
   │ (ClmStream)  │ ◀────────────────────────────────── │  (vLLM)   │
   └──────┬───────┘  (2) reply: one bash command        └───────────┘
          │ (3) write context file, run command, read file back
          ▼
   ┌───────────────────────────────────────────────────────────┐
   │ SANDBOX (proot root, one per trial)                        │
   │  /tmp/.live_ctx/LIVE_CTX_MAIN.txt   context file           │
   │  /tmp/ctx_offload/*                 files the model saved  │
   │  /tmp/.bash_ctx_state/{cwd,env}     persistent shell state │
   └───────────────────────────────────────────────────────────┘
```

Per turn (`clm_harness/context_env/env.py:ContextEnv.step`):
1. The harness writes `render_editable(messages, protect=2)` to the context file. Each
   non-pinned message becomes a block `[[CTX_TURN n role=…]]` + its text (reasoning,
   content, issued command).
2. It runs the model's command through `wrap()` (restores and saves cwd/env).
3. It reads the file back. If it changed, `parse_back` turns it into the new message list,
   unless the edit gate rejects it (gate `fit`: an edit that grows the context is refused
   if the result is over 32768 − 2048 = 30720 tokens).
4. The tool result (`StepResult.render()`) is appended; the stream appends the next op as a
   user message.

### Where the state lives

```
                     STATE AT TURN t
   ┌──────────────────────────────┬───────────────────────────────┐
   │ A. Message list (prompt)     │ B. Disk                       │
   │  • task + ops received       │  • /tmp/ctx_offload/*         │
   │  • whatever survived edits   │  • shell cwd / env            │
   │  • context file = A rendered │  • any other file written     │
   ├──────────────────────────────┼───────────────────────────────┤
   │ LOGGED (lm_log_proxy saves   │ NOT LOGGED (sandbox deleted   │
   │ every request)               │ after the trial)              │
   └──────────────────────────────┴───────────────────────────────┘
```

- **A decides what the model says.** Resending the logged request gives the model the exact
  same input.
- **B decides what a command does.** Example: writing `kv-0004.txt` is harmless if the file
  is new and destroys batch 4 if it already exists.
- B can be rebuilt: only the harness and the model's own commands write files, the task
  stream is deleted from the container at setup (`clm_contextbench/clm_stream.py:12`), and
  every command is in the log. Re-running the logged commands in order rebuilds B.

### The collection idea in one picture

```
 ORIGINAL TRIAL (done, logged)
 turn:   1 ──▶ 2 ──▶ 3 ──▶ 4 ──▶ 5 ──▶ 6 ...

 REPLAY (no model, re-run logged commands)
 fresh root ─▶ cmd1 ─▶ cmd2 ─▶ cmd3 ─▶ cmd4 ─▶ ┌ pause before turn 5: copy root = "pristine"
                                              └──────────────┬─────────────
            ┌──────────┬──────────┬──────────────────────────┼──────────────┐
            ▼          ▼          ▼                          ▼              ▼
         sample 1   sample 2    ...                       sample 9      sample 10
     (10 replies to the logged turn-5 prompt, generated earlier with vLLM n = 10)
     each: restore pristine ─▶ ContextEnv.step(sample cmd) ─▶ outcome label
                                              │
                         group equal outcomes ─▶ SE (bits)
                                              │
                         run the LOGGED cmd5 ─▶ continue to the next point
```

### Definitions

- **Decision point t:** one logged LM call whose command ran. Its prompt is `req_t`.
- **Block:** one `[[CTX_TURN n]]` section of `render_editable(req_t.messages)`.
- **Block label** after a command: `stay` (text unchanged), `edit` (partly kept),
  `offload` (removed, text found in a file the command wrote), `delete` (removed, not saved).
- **Clobber flag:** the command destroyed content of a file that existed before it
  (overwrite with `>`, delete, truncate). Appending with `>>` is not a clobber.
- **Sample status:** `ok`, `invalid` (exit ≠ 0 and context unchanged), `no_command` (reply
  has no bash tool call, e.g. thinking hit 8192 tokens), `context_status` (the unadvertised
  status tool).
- **Outcome key:** status if not `ok`; otherwise the tuple of block labels + clobber flag.
  Two samples are in the same cluster iff their keys are equal.
- **SE (bits):** `−Σ_c p_c log₂ p_c`, `p_c` = share of the 10 samples in cluster c.
  Range 0 to log₂ 10 = 3.32.

---

## Part 1. Collecting semantic entropy, step by step

Code: two files.
- `infra/semantic_entropy/entropy.py`: pure functions (no I/O): `outcome_key`, `label_blocks`,
  `cluster`, `se_bits`, `se_weighted_bits`. `__main__` = assert self-check.
- `infra/semantic_entropy/collect.py`: three passes per trial (`replay`, `sample`, `execute`), selected
  by a subcommand. Uses the harness's own code; nothing about the harness is re-implemented.

Output folder: `runs/m6-se/` (gitignored like the rest of `runs/`).

### Step 0. Prerequisites (on the pod)

0.1 **Check the log fields.** For one finished M5 trial:
```bash
f=$(ls runs/m5-lmlog/*.jsonl | head -1)
head -1 "$f" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(list(d)); \
  print(list(d["request"])); print(d["response"]["usage"]); \
  print(d["response"]["choices"][0]["message"].keys())'
```
Required per line:
- `request`: `model`, `messages`, `tools`, `temperature`, `top_p`, `max_tokens`,
  `chat_template_kwargs` (thinking on), and any other body field sent;
- `response`: full JSON with `choices[0].message` (`content`, `reasoning_content`,
  `tool_calls`) and `usage.prompt_tokens`.

Adjust the field names in Step 2 to whatever the proxy actually writes. If the full request
or response is missing, fix `lm_log_proxy.py` now; finished trials without it cannot be used.

0.2 **Version the proxy.** Copy `lm_log_proxy.py` from the pod into `infra/` and commit it.

0.3 **Python env.** Use the same venv as the harbor runs, with
`PYTHONPATH=context-language-models/clm:infra`. Check:
```bash
python3 -c "from clm_contextbench.clm_stream import ClmStream, PAPER_KWARGS; \
from clm_harness.context_utils.context_string import render_editable, parse_back; \
from chroot_env import ChrootEnvironment; print('ok')"
```

0.4 **Dev trials.** Pick two finished M5 trials: one 4B KV (R1000 or R4000), one 9B
LogTriage. All Gates below run on these two first.

### Step 1. Write `entropy.py` first (with its check)

Functions:
```python
def se_bits(counts: list[int]) -> float          # -Σ p log2 p
def se_weighted_bits(weights: dict[str, float]) -> float   # same on renormalized weights
def outcome_key(status, labels, clobber) -> str  # "invalid" | "no_command" | "stay|edit|...|C0"
def cluster(keys: list[str]) -> dict[str, int]   # collections.Counter
def label_blocks(before: str, after: str, written: str) -> list[str]
```

`label_blocks` algorithm:
1. Split `before` into blocks with the header regex `^\[\[CTX_TURN \d+ role=\w+\]\]$`
   (same as `parse_back`'s `_HEADER_RE`; import it instead of copying).
2. For each block body: `lines` = stripped non-empty lines with ≥ 8 characters (short lines
   like `}` or `PY` match anywhere and mean nothing).
3. Label:
   - whole body (whitespace-normalized) is a substring of normalized `after` → `stay`;
   - else ≥ 1 of its `lines` in `after` → `edit`;
   - else ≥ 90% of its `lines` in `written` → `offload`;
   - else → `delete`.
   - Body with no `lines` at all: `stay` if present, else `delete`.

Self-check in `__main__` (numbers from the worked examples):
```python
assert se_bits([10]) == 0
assert round(se_bits([5, 3, 2]), 2) == 1.49
assert round(se_bits([6, 2, 1, 1]), 2) == 1.57
assert round(se_bits([9, 1]), 2) == 0.47
# label_blocks on a 3-block toy context: kept / cut and saved / cut not saved
assert label_blocks(TOY_BEFORE, TOY_AFTER, TOY_WRITTEN) == ["stay", "offload", "delete"]
```

### Step 2. Load a trial log into a turn list

```python
@dataclass
class Turn:
    k: int                 # index among turns whose command ran
    req: dict              # logged request body
    resp: dict             # logged response
    assistant: dict        # resp.choices[0].message, after _extract_tool_call
    cmd: str               # the bash command
    tool_content: str      # the role=tool message that follows it in the next request
    fill: float            # resp.usage.prompt_tokens / 32768
    turn_type: str         # "context_edit_turn" if "edit applied" in tool_content,
                           # else "context_stay_turn"
```

Procedure:
1. Read all lines in order. For each line, run `clm_agent.harness._extract_tool_call` on a
   copy of the response message. Keep only `type == "bash"` calls.
2. A call k "ran" if the next request contains a `role=tool` message with that call's
   `tool_call_id`. Calls with no next request (the last call) ran if the trial's
   `clm_stream.json` says it ended by `submit`.
3. Drop calls that did not run (overflow retries, no tool call, `context_status`).
4. Check: number of kept turns = number of bash steps in the trial's timing log
   (`timing_log` entries with a `bash_s` field). Mismatch = stop and look.

### Step 3. Build harness objects for replay

1. **ContextEnv with the run's exact settings.** Build the agent the way harbor did and take
   its `ContextEnv`, so budget, gate, observation caps and paths match the run:
   ```python
   agent = ClmStream(logs_dir=tmp_logs, model_name="openai/<served-name>", **PAPER_KWARGS)
   ctx = agent._ctx           # ContextEnv; agent._budget is its BudgetController
   ```
   If the constructor needs more harbor arguments, copy them from how
   `infra/run_cb_trial.sh` launches the trial. Do not hand-build `ContextEnv` unless this
   fails; if you must, copy every argument from `clm_agent/harness.py:334-344`.
2. **Sandbox.** Build `ChrootEnvironment` the way harbor does for this task
   (`data/cb_tasks/<task>`; constructor args from harbor's `BaseEnvironment`), with its own
   root under `runs/m6-se/roots/<trial>/main`. Call `await env.start(force_build=False)`,
   then `await ctx.setup_dirs(env)`.
3. Use the rootfs that M5 used (`/root/rootfs`, digest in `py312slim.digest`). Record the
   digest in the output.

### Step 4. Pass 1: replay only, find divergence (CPU, can run now)

```python
for turn in turns:
    msgs = copy.deepcopy(turn.req["messages"])
    agent._budget.calibrate(turn.resp, msgs)          # as the harness does after each call
    obs = await ctx.step(turn.cmd, msgs, environment=env, pending=turn.assistant)
    got = ctx.append_submit_warning(turn.cmd, obs.render())
    if got != turn.tool_content:
        diverged_at = turn.k; save diff (first 500 chars each side); break
```

- `ctx.step` writes the context file from `req_k`, runs the command, applies the gate:
  exactly what the run did.
- Equality is the target. If the only differences are in harness notes that depend on
  counters (not on disk), compare the stdout part only (`obs.stdout_block` must be a prefix
  of `turn.tool_content`) and note which notes differ.
- Write `runs/m6-se/<trial>.replay.json`: `n_turns`, `diverged_at` (or null), digest.

**Gate A:** on the 2 dev trials, no divergence, or divergence only after ≥ 95% of turns.
Otherwise find the cause (time, `$RANDOM`, `ls -t` ordering, rootfs) before going on.

### Step 5. Choose decision points

From the turn list, within `k < diverged_at`:
1. all `context_edit_turn`s;
2. plus 20 `context_stay_turn`s, 5 from each fill bin [0, .25), [.25, .5), [.5, .75), [.75, 1]
   (fewer if a bin is short), random with `seed = int(sha256(trial).hexdigest()[:8], 16)`;
3. cap 40 (if over, keep all `context_edit_turn`s in the top fill bin first, then random).

Write `runs/m6-se/<trial>.points.json` (list of k).

### Step 6. Pass 2: sample (GPU, after M5 frees the card)

For each point t:
1. `body = copy.deepcopy(turns[t].req)`; set `n = 10`, `logprobs = True`,
   `seed = hash(trial, t) % 2**31`. Keep every other field as logged.
2. POST to the model server directly (`:8000` 4B, `:8010` 9B), not through the logging
   proxy, so M5 logs stay clean.
3. **Check:** `resp.usage.prompt_tokens == turns[t].resp.usage.prompt_tokens`. Mismatch →
   stop; the template, tools or `chat_template_kwargs` differ.
4. For each of the 10 choices: run `_extract_tool_call` on the message → command or status
   (`no_command`, `context_status`). Mean token logprob → `logprob_norm`.
5. Append one line per point to `runs/m6-se/<trial>.samples.jsonl.gz` (raw choices + parsed
   command + status). Skip points already in the file (resumable).

Run up to ~8 points concurrently per server; all 10 samples share the prompt, so prefix
caching makes the prefill cheap.

### Step 7. Pass 3: replay again, execute samples, label (CPU)

Same loop as Step 4, plus work at each point t, **before** running the logged `cmd_t`:

```python
pristine = roots/<trial>/pristine;  work = roots/<trial>/work
cp -a  main/  pristine/                  # disk exactly as the model had it at turn t
data_before = read_data_files(pristine)  # {path: bytes} under /tmp, excluding
                                         # /tmp/.live_ctx and /tmp/.bash_ctx_state
before_text = render_editable(req_t.messages, protect=2)

for s in samples[t]:
    if s.status != "ok": record(s.status); continue
    rsync -a --delete pristine/ work/        # fresh copy of turn-t disk
    touch work/.se_marker
    ctx_s = fresh ContextEnv (Step 3.1)      # counters must not leak between samples
    msgs = copy.deepcopy(req_t.messages)
    obs = await ctx_s.step(s.cmd, msgs, environment=env_on(work), pending=s.message)
    after_text = render_editable(msgs, 2)    # msgs changed in place only if gate accepted
    written = files under work/ newer than .se_marker (excluding ctx/state dirs), concatenated
    data_after = read_data_files(work)
    if obs.result.return_code != 0 and not obs.ctx_changed:
        status = "invalid"
    else:
        labels  = label_blocks(before_text, after_text, written)
        clobber = any(old not in concat(data_after.values()) for old in data_before.values())
    key = outcome_key(status, labels, clobber)
    record(sample fields, key, obs.result.return_code, len(after_text))

rm -rf pristine
# then run the logged cmd_t on main/ (Step 4 body) and continue
```

Notes:
- `env_on(work)`: a `ChrootEnvironment` whose root is `work/` (same class, different root;
  do not call `start()` on it, which would recopy the template).
- A rejected edit leaves `msgs` unchanged, so all blocks label `stay`; disk effects (files
  written, clobber) still count. This matches what the real harness would do.
- Command timeout = the run's (`ctx.command_timeout`). A timeout counts as `invalid`.

**Gate B (labeller self-consistency):** at each point, also label the logged `cmd_t` with the
same code, from `main/`. Then check that the logged command's `after_text` equals
`render_editable` of the first `len(msgs)` messages of `req_{t+1}` (what the harness really
sent next). Target 100% on the 2 dev trials; each miss is a bug in the labeller or replay.
Then read 10 random sample labels by hand against their commands.

### Step 8. Entropy and output

Per point:
```python
counts = cluster([s.key for s in samples])
se = se_bits(list(counts.values()))
w  = {key: Σ exp(s.logprob_norm) over samples with that key}
se_w = se_weighted_bits(w)
```
One line per point in `runs/m6-se/<trial>.jsonl`:
```json
{"trial": "...", "model": "4B", "family": "kv_store", "level": "R4000", "seed": 46,
 "reward": 1.0, "t": 5, "fill": 0.81, "turn_type": "context_edit_turn", "logged_key": "stay|delete|offload|C0",
 "clusters": {"stay|delete|offload|C0": 6, "stay|delete|offload|C1": 2, "invalid": 1, "...": 1},
 "se_bits": 1.57, "se_weighted_bits": 1.61, "n_invalid": 1, "n_no_command": 0,
 "rootfs_digest": "sha256:05a994d2..."}
```
Needle only (open decision 1): split `edit` clusters further by the set of verbatim
`NEEDLE` lines kept in `after_text`.

### Step 9. Run everything

```bash
# Pass 1 now (CPU), one process per trial, ~12 at a time (pod has ~16 cores)
ls runs/m5-lmlog/*.jsonl | xargs -P 12 -I{} python3 infra/semantic_entropy/collect.py replay {}
python3 infra/semantic_entropy/collect.py points runs/m5-lmlog/*.jsonl
# Pass 2 after M5 frees each GPU
python3 infra/semantic_entropy/collect.py sample --api http://localhost:8000/v1 runs/m5-lmlog/*4b*.jsonl
python3 infra/semantic_entropy/collect.py sample --api http://localhost:8010/v1 runs/m5-lmlog/*9b*.jsonl
# Pass 3 (CPU)
ls runs/m5-lmlog/*.jsonl | xargs -P 12 -I{} python3 infra/semantic_entropy/collect.py execute {}
```
(Exact log filename patterns: check against `runs/m5-lmlog/`.)

- Every pass is resumable: it skips trials/points already done.
- Disk: one pristine + one work root per running trial (two rootfs copies; measure with
  `du -sh /root/rootfs`). Delete roots when a trial finishes.
- Estimate: 84 trials × ~30 points × 10 samples ≈ 25k generations, ~1.5k output tokens
  each; a few hours per model on one A40.

### Step 10. QA report before analysis

`runs/m6-se/qa.md` (and the summary in `.agent/notes/m6-se-results.md`): per trial, turns,
divergence turn, points, `invalid` and `no_command` rates, Gate B pass rate; SE histogram
per model × family × level; 5 hand-read points (highest SE) with their clusters.

---

## Part 2. Correlation analysis (H1)

**Unit = trial.** Trial summaries, fixed now: mean SE, max SE, mean SE over points with
fill ≥ 0.75.

1. Load all `runs/m6-se/*.jsonl` into one table (pandas).
2. **Main test:** Spearman ρ(trial mean SE, reward), **partial on pressure level** (rank-
   residualize both on level dummies, then Spearman), **separately per model**. 95% CI by
   bootstrap over trials (2000 resamples).
3. **Regression:** `reward ~ mean_SE + C(level) + C(family)` per model (OLS; fractional
   logit as a check). Report the SE coefficient and ΔR² over the model without SE.
4. **Plots:** SE vs pressure and reward vs pressure per model × family; SE vs reward
   coloured by level.
5. **Step level (where ground truth exists):** label each `context_edit_turn` *harmful* if it
   deleted (not offloaded) or clobbered content needed later: KV = a SET whose key is later
   GET-ed and answered wrong; LogTriage = a batch not on disk when asked. AUROC of point SE
   for harmful edits.

**Go/no-go to Part 3 (fixed now):** Go if partial |ρ| ≥ 0.3 with the CI excluding 0 in at
least one model, **or** step-level AUROC ≥ 0.65. "Strong" = |ρ| ≥ 0.5. n ≈ 42 trials per
model; ρ = 0.3 needs ~85 for 80% power, so pool 4B + 9B with a model term if one model alone
is under-powered.

## Part 3. Linear probe (H2, only on Go)

1. **Activations:** HF transformers forward pass (no generation) on each point's
   `req_t` rendered with the same chat template (check the token count equals the logged
   `prompt_tokens`), `output_hidden_states=True`. Save the residual stream at **TBG** (last
   prompt token) and **SLT** (last token of the logged response, forward pass over prompt +
   response), all layers, float16, to `runs/m6-probe/<trial>.npz`. Up to 32k tokens fits an
   A40 with SDPA and `torch.no_grad()`.
2. **Targets:** (a) binary SE at γ* (Kossen: threshold minimizing summed within-group squared
   error), logistic regression → AUROC; (b) continuous SE, ridge → Spearman / R²;
   (c) for comparison, a direct probe for reward / harmful edit.
3. **Splits:** 5-fold group k-fold **by trial** (adjacent turns would leak otherwise). Layer
   and regularization chosen on inner folds only.
4. **Controls (must beat):** shuffled labels; a probe on (fill, turn index) alone; a probe on
   SE residualized on fill. If activations do not beat the fill-only probe, SE is just
   encoding context length (the Du et al. confound in [`notes/literature.md`](notes/literature.md)).
5. **Output for H3:** probe weight vector and difference-of-means direction at the best
   layer, saved with the layer index.

---

## Experiment config (M6)

**Control (from M5, unchanged):**
- Trials: M5 KV + LogTriage, 4B and 9B, `skill=clm`, `CB_SETTINGS=paper` (32768 / 2048, no
  nudges, edit gate `fit`), 4 pressure levels, M5 seeds.
- Serving: vLLM 0.33.0, BF16, prefix caching on, same model per arm as the trial.
- Replay sandbox: M5 rootfs (same digest), proot, persistent bash on, harness `ContextEnv`
  built from `PAPER_KWARGS`.
- Sampling: T 0.7, top_p 0.95, thinking on, max_tokens 8192 (= the run's).

**Vary / new:**
- **K = 10 samples per decision point.**
- **≤ 40 points per trial** (all `context_edit_turn`s + 20 fill-stratified `context_stay_turn`s).
- **Outcome classes: stay / edit / offload / delete + clobber flag; invalid, no_command,
  context_status.**
- **Entropy in bits** (discrete primary, likelihood-weighted secondary).
- Model: 4B / 9B (9B-RL if its M5 arm finishes).

## Risks

1. **Log completeness (blocking):** without full request and response bodies nothing can be
   replayed. M2 trials were not proxied; usable only if harbor's trial logs hold full prompts.
2. **Recipe floor:** with `skill=clm` the 4B runs a fixed KV/LogTriage recipe, so its SE may
   be ~0 almost everywhere. Signal then comes from deviations (mostly the 9B). Report the SE
   distribution first; add **Needle** (where keep/delete is a real judgement) if flat.
3. **Pressure confound:** pressure drives both SE and reward. Always report partial /
   within-level numbers, never only pooled ρ.
4. **Replay non-determinism:** `date`, `$RANDOM`, `ls -t`. Gate A finds the first divergence;
   points after it are dropped.
5. **Rootfs drift:** M5's rootfs digest may differ from M2's. Replay M5 trials on M5's rootfs.
6. **Conditional SE:** uncertainty is measured given the realized history up to t. Earlier
   turns are not re-rolled; that would be a different (trajectory-level) quantity.

## Open decisions

1. Needle second-level clustering: verbatim needle-set match instead of entailment
   (recommended; Needle is graded on verbatim lines).
2. Add Needle trials if KV/LogTriage SE is near 0 almost everywhere.

## Milestones

| # | Done when |
|---|---|
| 0 | Log fields confirmed; `lm_log_proxy.py` in `infra/` |
| 1 | `entropy.py` self-check passes |
| 2 | Pass 1 passes Gate A on 2 dev trials |
| 3 | Pass 3 passes Gate B on 2 dev trials; 10 labels hand-checked |
| 4 | SE for the 2 dev trials; distribution and 5 high-SE points read |
| 5 | Full run on all M5 trials; QA report written |
| 6 | Part 2 analysis; go/no-go recorded in `decisions.md` |
| 7 | (Go) Part 3 probe results in `notes/m6-probe-results.md` |

---

## Amendment (post-hoc, 2026-11-16): decision-only SE

Not pre-registered; added after the full 9B and 9B-RL runs to answer "is SE just tool-use uncertainty?". The
pre-registered SE stays the headline; this is a robustness analysis. Results: [`notes/m6-se-results.md`](notes/m6-se-results.md)
("Is H1/H2 driven by tool-use uncertainty?"); paper §3.6, §5.7, §6.2; handoff [`handoff/handoff-m6-paper.md`](handoff/handoff-m6-paper.md).

- **Motivation:** status outcomes (`invalid` = non-zero exit and no context change, `no_tool_call`,
  `context_status`, `error`) are clusters in the outcome key (Part 1), so SE mixes *which context decision* with
  *whether the command / tool call works*. At baseline 36% of SE > 0 points involve a status cluster (format
  failures are only 0.2% of samples, so this is mostly failed commands).
- **Decision-only SE** per point: discrete SE over the samples with status `ok` only; points with fewer than 2 `ok`
  samples are dropped (NaN). Trial summary = mean over points.
- **Status-only SE** per point: entropy of the status variable with every `ok` sample merged into one outcome
  (`ok`, `invalid`, `no_tool_call`, …).
- **Part 2 (H1) with these:** the same partial Spearman (rank-residualized on family × level, 2000 bootstrap
  resamples over trials) and OLS `reward ~ x + C(family:level)` for each measure, plus a joint OLS with both.
- **Part 3 (H2) with these:** TBG activations at a fixed layer (9B: 20, 9B-RL: 28, the layers the original probes
  selected), same 5-fold GroupKFold by trial, logistic (C 0.05) for `> 0` targets and ridge (α 1000) for the
  continuous target, standardized features; control = fill + turn index. Points with NaN decision-only SE dropped.
- **Code:** `infra/semantic_entropy/decision_only.py` (`h1`, then `h2`).
