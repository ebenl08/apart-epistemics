# Decisions Log

Every major decision, newest last. Format: date, time, header, description.

## 2026-11-14 17:49 +08 — Ask before every commit
After every experiment or change, ask the user whether to commit to GitHub. Never commit or push unprompted.

## 2026-11-14 17:49 +08 — Clean commit standard
Conventional Commits (`type(scope): imperative summary`, ≤50 chars), body wrapped at 72 cols explaining why, atomic commits, explicit staging, tests before commit.

## 2026-11-14 17:49 +08 — AGENTS.md added to context-language-models
Repo-level agent guide (layout, setup, test command, conventions, commit rules) at `context-language-models/AGENTS.md`. Not yet committed.

## 2026-11-14 17:49 +08 — NOTES.md product specification
Full feature spec of the CLM repo at `context-language-models/NOTES.md`, built from READMEs and code. Unverified claims are marked. Not yet committed.

## 2026-11-14 17:49 +08 — Session workflow rules
1. After each decision, suggest updating `handoff/handoff-<session-name>.md`.
2. Log every major decision here (ask the user if unsure it is major).
3. Compact when the 250k-token limit is hit, then update the session's handoff.

## 2026-11-14 18:12 +08 — Milestone checkpoints in every plan
Every plan defines milestones (subgoals/checklist items). After each single milestone is completed, stop and ask the user for clarification before continuing, unless the user says otherwise for that plan.

## 2026-11-14 +08 — Literature search done first
User chose to do the literature search before any code. Output: `.agent/literature.md` (~45 entries, agent-verified links; "snippet" entries not opened). Gap: no existing work tests uncertainty on model-driven edit decisions. Top picks: CLM 2609.37725, Self-Compacting LM Agents 2606.23525, Lost in Context Compaction 2608.11242, Do I Know This Entity 2411.14257 + refusal direction 2406.11717, Two Axes of Abstention 2607.08456.

## 2026-11-14 +08 — Qwen3.5-4B for reproduction and interp
Use Qwen3.5-4B (not Qwen3.6-27B) so the same model serves reproduction and mech interp. Go/no-go via smoke test; fall back to Qwen3.5-9B if 4B cannot edit context. Plan in `.agent/instruction-reimplementation.md`.

## 2026-11-14 +08 — ContextBench first, BCP second
ContextBench runs from the repo; BCP needs corpus, search skill and judge built. Reproduction target for ContextBench is the paper's App. F no-skill Qwen3.6-27B numbers, not Fig 2 (GPT-5.4).
