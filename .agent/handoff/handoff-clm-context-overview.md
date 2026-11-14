# Handoff: CLM context overview

Session: clm-context-overview
Written: 2026-11-14
Project goal (from `.agent/instructions.md`): Apart Research AI x Epistemics sprint, Track 4 Open Track. Study whether context-management quality in a Context Language Model (CLM) links to model epistemic uncertainty.

## State

Read-only study of the CLM repo. No code was written or changed. Nothing to commit from this session.

The repo now lives at `external/context-language-models/` (it was at `context-language-models/` earlier in the session). Paths below use the new location. `NOTES.md` mentioned in `decisions.md` does not exist at that path; `AGENTS.md` does.

## What was learned

Source paper: https://arxiv.org/abs/2609.37725. Repo: https://github.com/facebookresearch/context-language-models.

### Context is one file per agent
- The released harness (`clm-minimal`) gives the model one `bash` tool. The harness mirrors the editable context to `/tmp/.live_ctx/LIVE_CTX_MAIN.txt` before every command. The model compacts by editing that file with `sed`, `python3` or `cat >`.
- The mirror is only for editing. The model's input each turn is the normal message list, rebuilt from the file by `parse_back` when the file changed.
- Multi-agent contexts (one file per agent) are described in the paper but removed from the release: `subagents`, `n_subagent_slots` etc. are in `_REMOVED_KWARGS` in `clm/clm_harness/clm_agent/harness.py`.

### File layout
- The system prompt and task are pinned and are not in the file (`protect=2`).
- Every later turn is a block: `[[CTX_TURN i role=...]]` then the turn text (reasoning, content, and the issued command). Numbering starts at 1 after the pinned prefix.
- `parse_back` is tolerant: it re-pins the prefix, recovers turns from surviving headers, drops empty turns, merges consecutive same-role turns, and turns every non-assistant role into `user`. Tool-call structure is lost across an edit.

### Who decides what to keep or delete
- The model decides, in an ordinary LM turn. No retriever or scorer picks spans. No per-turn user query: the task is fixed in the pinned prefix.
- The harness only controls when and whether: nudges at 25/50/75% of budget, an adaptive urgent nudge, rollback and retry above the limit, and an edit gate (`fit` = accept if it fits the limit, `shrink` = accept only if smaller). The gate checks token count only, not semantic quality. This matters for the research question: bad summaries pass the gate.
- A turn that only edits the mirror, prints nothing and exits 0 is free (no task step).

### Steering and training
- In-context steering (`clm/clm_icl`): a `SKILL.md` appended to the system prompt. A proposer model reads contrastive success/failure rollouts and writes N candidate skills. Candidates are run on dev tasks and a statistical gate (d > SE, or tie and cheaper) decides replacement.
- RL (`clm/clm_rl`): dual-channel advantage. Task reward goes to all tokens. An efficiency bonus (FLOPs with prefix-cache reuse) goes only to tokens of turns that edit the mirror. RL training code is not in the repo (ProRL-Agent-Server and Slime patches only).

### Serving cost: Suffix Cache Reuse (SCR)
- Editing the middle of the context breaks the prefix cache. SCR (`suffix_cache_reuse/`, vLLM 0.19.1 and SGLang) reuses KV for surviving text.
- Detection does not use vLLM's hash chain. SCR keeps the previous prompt's token IDs per conversation, matches the new prompt to a conversation (`find_session`), diffs token IDs with content-defined chunking plus `SequenceMatcher` (`diff_opcodes`), and plans up to K=6 spans of at least 64 tokens (`plan_relocation`). The previous request's prompt blocks stay pinned (`ref_cnt += 1`) so the old K/V can be copied and RoPE-re-rotated into the new positions.
- Caveat: relocated K/V are stale (computed under the old prefix). Only position is corrected.
- Worked example (real planner output, toy sizes): old = A(40) B(30) C(50), new = A(40) B'(8) C(50) D(10). Prefill drops from 68 to 22 tokens.

## Relevance to the research plan

Plan from `instructions.md`: (1) reproduce CLM on ContextBench, (2) elicit context-uncertainty behavior, (3) test an uncertainty direction causally.

Observations that bear on it:
- Edit decisions are visible as file diffs between `rendered` and `read_back` in `ContextEnv.step` (`clm/clm_harness/context_env/env.py`). Each applied edit has before/after token counts (`edit_rec`). Counters exist for real edits, growth and rejections (`n_ctx_syncs_real`, `n_ctx_grew`, `n_ctx_rejected`).
- Per-call `context_snapshots/` and `trajectory.ctx.json` (ATIF-CTX) record intermediate context segments. These are the natural data source for "what did the model drop, and was it needed".
- Trivial edits (under 32 tokens or 1% of editable context) are counted as noise.
- Nudges and budget pressure are confounds: edit aggressiveness may follow the harness thresholds, not model uncertainty. Any elicitation experiment must control for them.
- Possible intervention point for the "uncertainty labels in the context file" idea: `render_editable` / the turn header format, plus the `edit_gate`.

## Open items

- Nothing run yet. No baseline reproduced. Not verified: ContextBench task setup, whether the local server/model needed for runs is available.
- Not read in full: `clm/clm_harness/utils/budget.py`, `clm/clm_contextbench/clm_stream.py`, `clm/clm_icl/note.py`, SGLang `overlay.py`.
- Literature search on context uncertainty is the next task named in `instructions.md`; not started in this session.
- Earlier answers in this session linked to `file:///Users/ebenlim/Projects/apart-epistemics/context-language-models/...`. Those links are stale; use `external/context-language-models/...`.

## Key files (under `external/context-language-models/`)

- `clm/clm_harness/context_utils/context_string.py`: `render_editable`, `parse_back`
- `clm/clm_harness/context_env/env.py`: per-turn `step`, edit counters
- `clm/clm_harness/context_env/edit_gate.py`: fit/shrink gate
- `clm/clm_harness/clm_agent/prompts.yaml`: system prompt and compaction instructions
- `clm/clm_harness/README.md`: settings table
- `clm/clm_icl/README.md`, `clm/clm_icl/proposer_prompt.md`: skill evolution
- `clm/clm_rl/README.md`: dual-channel advantage
- `suffix_cache_reuse/vllm/DESIGN.md`, `suffix_cache_reuse/vllm/vllm_scr/planner.py`: SCR
