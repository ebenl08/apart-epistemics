# Handoff: literature search, paper read, reproduction plan

Session: literature-search
Updated: 2026-11-14
Goal: see `.agent/query.md` (Apart sprint Track 4: CLM context management vs epistemic uncertainty).

## State

- `.agent/notes/literature.md`: ~45 entries over 6 areas, gap analysis, top 5, 5 edit-policy ideas. Committed in `2c86aac`.
- `.agent/instruction-reimplementation.md`: step-by-step plan for reproducing CLM on ContextBench and BCP with Qwen3.5-4B. **Next session starts here.** Not committed.
- The repo moved from `external/context-language-models/` to `context-language-models/` (project root). `.gitignore` still only ignores `external/`, so this needs fixing.
- The paper PDF is at the project root: `Context Language Models.pdf`. `Read` can't render it (no poppler). Extract with `gs -sDEVICE=txtwrite`; spaces get stripped but the text is readable.
- Nothing run yet.

## Key findings from the paper (main body + App. D-G)

- The ContextBench 24× sweep (Fig 2) is **GPT-5.4**, not Qwen. Qwen3.6-27B numbers only appear in App. F (in-context evolution start, no skill): Needle 97.6, Sudoku 45.3, KV Store 22.3, Log Triage 0.0 (dev). KV test 38.3 → 74.2 with the evolved skill. Not at ceiling.
- Needle Retention labels the needles, which removes uncertainty by design. For elicitation, make relevance ambiguous instead.
- App. G: context-length awareness degrades at long lengths, and token-count hints fix it. The harness injects hints, so record the hint setting as a confound.
- RL section: rewarding edit volume leads to reward-hacking deletions. This supports the aggressive-deletion framing.
- Qwen3.5-9B CLM: 28.8 → 42.5 on BCP after RL. 9B is weak before RL, so 4B may floor.
- PFLOPs vs accuracy (Fig 5) is a reporting axis for the reproduction and for any uncertainty gate (does it move the Pareto frontier?), not an uncertainty measure.

## Model decision

- Qwen3.5-4B (mech interp needs a small model). Config verified: 32 layers, hidden 2560, hybrid 3 linear-attention : 1 full-attention, vision tower.
- HF RL checkpoints exist: `rl-ckpt-b0sum_dapo-iter49` (confirmed Qwen3.5-9B-Base fine-tune, likely the summary arm) and `rl-ckpt-livectx_dapo-iter44` (likely the CLM arm, base not stated, may be gated).
- There is no Qwen3.6 model under 27B.

## Next

1. Decide hardware (see the open decisions in `instruction-reimplementation.md`).
2. Steps 0-2: environment, serve 4B, smoke test (go/no-go).
3. ContextBench conditions A/B, then BCP (needs corpus, search skill and judge built; not in repo).
4. Then draft `plans.md` for elicitation (agreed with the user: synthetic planted items + resampled edit disagreement + labels).
