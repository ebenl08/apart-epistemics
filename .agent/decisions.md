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

## 2026-11-14 +08 — Reproduction subset
ContextBench: KV Store + Sudoku only, `skill=clm` paper kwargs, 4 pressure levels × 2 seeds (16 trials). No skill-evolution condition. BCP: 50-question subset, judge Qwen3.5-27B-GPTQ-Int4. Hardware: A40.

## 2026-11-14 +08 — ContextBench without skills
Use `skill=none` with App. F settings (32000 budget, 4096 reserve, 240 turns) instead of `skill=clm`, to compare with the paper's Qwen3.6-27B no-skill numbers (KV 22.3%, Sudoku 45.3%).

## 2026-11-14 +08 — Final reproduction setup
A40 hardware. ContextBench: KV Store + Sudoku, `skill=none`, App. F settings, levels 0.5×/2×/8×/24× × 2 seeds (16 trials), timeout 28800 s. BCP: 50 questions, `bcp.yaml`, judge Qwen3.5-27B-GPTQ-Int4. All trials concurrent, longest first. Supersedes the earlier subset entry.

## 2026-11-14 15:52 UTC — Chroot sandbox instead of Docker (option 3)
Host is a RunPod container: 1x A40, 96 cores, no Docker/Singularity, no CAP_SYS_ADMIN (no mounts or namespaces), but CAP_SYS_CHROOT. Harbor trials run through a custom environment `infra/chroot_env.py:ChrootEnvironment`: a private copy of the python:3.12-slim rootfs per trial (pulled from Docker Hub, digest in /root/rootfs/py312slim.digest). Deviations from Docker: no CPU/memory limits, no network isolation, no /proc, /dev/null is a regular file truncated before every exec (mknod blocked). User chose option 3 (serve the model now, work out the sandbox in parallel).

## 2026-11-14 15:52 UTC — Serving: vLLM 0.33.0, one shared server
Qwen3.5-4B BF16 on vLLM 0.33.0 (`infra/serve_qwen35_4b.sh`): max-model-len 65536, `--language-model-only`, parsers qwen3_coder/qwen3 (confirmed by the model card), prefix caching on. KV cache 945k tokens. Only 1 GPU, so ContextBench and BCP share this server.

## 2026-11-14 15:52 UTC — ContextBench under data/
ContextBench cloned at `data/ContextBench` (commit fb533c1), packaged tasks in `data/cb_tasks` (KV + Sudoku, seeds 42/43, agent timeout 28800 s). `data/` is gitignored (user request).

## 2026-11-14 17:51 UTC — M1 result: keep Qwen3.5-4B, use skill=clm
M1 + M1b (seed 42, KV R260 / Sudoku t8): 4B+none 0/24, 7/8; 4B+clm 22/24, 0/8 (one dropped move); 9B+none 0/24, 6/8. No model edits context without the skill; 9B does not help. Keep 4B (mech interp). ContextBench reference becomes the paper's CLM condition (skill=clm), not App. F no-skill. Details: `.agent/notes/m1-smoke-results.md`.

## 2026-11-14 17:51 UTC — Sandbox switched to proot
User approved installing proot (apt, 5.1.0). `infra/chroot_env.py` now runs commands under proot with host /proc, /dev, /sys bound, so /dev/fd, /dev/stdin and process substitution work as in Docker. Remaining deviations: no CPU/memory limits, no network isolation, host /proc visible.

## 2026-11-14 17:51 UTC — Sudoku levels from paper.yaml only
Sudoku has no 24x rung. Use the available paper.yaml levels nearest the plan: t8 (0.53), t30 (1.67), t60 (3.23), t150 (8.01). KV: R260 (0.46), R1000 (1.57), R4000 (6.04), R16000 (23.93).

## 2026-11-14 17:51 UTC — runs/ gitignored
Trial outputs and logs under `runs/` stay local (user request).

## 2026-11-14 17:51 UTC — BCP smoke test before M2/M3
User asked to smoke-test BrowseComp-Plus with 4B before running M2/M3.

## 2026-11-14 17:57 UTC — HF cache and derived data on the local disk
`/workspace` is a quota-limited persistent volume (writes failed at ~54 GB). HF cache moved to `/root/hf_cache` (27 GB: Qwen3.5-4B, Qwen3.5-9B), with a symlink at `/workspace/.cache/huggingface` so the RunPod `HF_HOME` still resolves; serve scripts set `HF_HOME=/root/hf_cache`. BCP index and doc store go to `/root/bcp_index`. The local disk is container storage: it does not survive pod re-creation, so weights and the index must be re-downloaded or rebuilt then (user request).

## 2026-11-14 18:24 UTC — Sprint scope: BCP smoke + KV only, no judge
User: run the BCP smoke (5 q) and M2 KV concurrently; drop Sudoku (M3) this sprint because the in-place sketchpad dropped the first move in M1; skip the BCP LLM judge for now (provisional substring grader; answers kept for later judging). M2 uses `skill=clm` with `PAPER_KWARGS` as-is (`CB_SETTINGS=paper` in `infra/run_cb_trial.sh`): 32768 / 2048, no step cap, since 240 steps would cut R16000 (184 ops). GPU/CPU logged by `infra/util_log.sh`.

## 2026-11-14 18:52 UTC — Skip Sudoku (M3) this sprint
User rule: skip Sudoku if it stays problematic. Smoke (4B + clm, t8, paper settings): seed 42 scored 0/8 again (final board 255/256 cells, `reward_final_cell` 0.996), the same single dropped move as M1; seed 43 scored 8/8. The slip reproduces on seed 42 (2/2 runs), and exact-match versioned grading turns one slip into 0, so higher levels would mostly measure where the first slip lands. No full Sudoku run; tasks stay in `data/cb_tasks` for later. LogTriage and Needle added instead (packaged, seeds 42/43).

## 2026-11-14 18:52 UTC — Sandbox roots made unique per trial
`infra/chroot_env.py` named the trial root `<task>__env`, so two concurrent trials of the same task (skill none vs clm) shared and deleted one root (StreamIdentityError in 7 smoke trials, all rerun). Root now gets a random 8-hex suffix.
