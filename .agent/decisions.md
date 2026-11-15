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

## 2026-11-14 19:02 UTC — BCP: run the 50-question sample with our method text (v3)
BCP as configured answered 0/5 (4B never offloads search results). Our variant v3 puts a KV-style offload recipe + "keep a provisional answer on disk" into the task instruction and wraps tool outputs in id'd blocks: 2/5 correct on the smoke set (v2, same text in the system prompt: 1/5). Rule fixed before the run (≥2/5 answered → run 50) met, so the 50-question sample runs with v3, labeled as our deviation from the paper (no BCP method text there). Graded with the substring grader only; judge deferred.

## 2026-11-15 — M5: ContextBench seed sweep, 4B vs 9B vs 9B-RL (planned)
User: focus on ContextBench (BCP paused); raise to 8 seeds per level so we can test whether 9B accuracy falls as pressure rises; add the paper's CLM-arm RL checkpoint, pinned: `context-language-model/rl-ckpt-livectx_dapo-iter44` @ `ffc4aab2f30cb5b802ced6c84e6590ab5fec213d` (`converted/`, card says the base is Qwen3.5-9B-Base, RL on OpenResearcher, so ContextBench is a transfer test). Core = KV + LogTriage (148 new trials); Needle optional (4B Needle score reflects whether it copies the recipe correctly). Plan, time estimate and GPU-count options: `.agent/instruction-seed-sweep.md`. Every LM call must be logged before the runs (needed for step 2).

## 2026-11-15 07:25 UTC — M5 launched on a new 2×A40 pod
Pod `ia4u423t1fi61l` (template mpye6w4gcy, 2×A40, EU-SE-1, container disk 100 GB, network volume hri0q37of4 at /workspace, $1.18/h; CPU quota ~16 cores). Created via RunPod REST v2 (v1 retired today). Env rebuilt by `infra/setup_pod.sh` + `infra/pull_rootfs.py` (python:3.12-slim amd64 digest sha256:05a994d2…; may differ from the M2 rootfs). Weights on container disk, not the volume (user: no need to persist models). New seeds only (user): KV R260 s44–49, R1000/R4000/R16000 s46–49, LogTriage all 4 levels s44–49 = 42 trials per model; tasks copied from `data/ContextBench/tasks` with timeout raised 14400 → 28800 (as M2). GPU0 4B :8000, GPU1 9B :8010 (8001 is RunPod nginx). Every LM call is logged via `infra/lm_log_proxy.py` (:9000 / :9001) to `runs/m5-lmlog/<run>__<task>.jsonl`. All 42 trials per model run at once (N=48). 9B-RL (pinned ffc4aab) downloads after the 9B batch starts if > 30 GB disk is free, and runs on whichever GPU frees first.

## 2026-11-15 — M6 planned: semantic entropy of context decisions
Uncertainty measure = discrete semantic entropy (Farquhar 2024), total uncertainty, over K=10 replays of each logged LM call. Equivalence = identical per-block outcome vector (stay/edit/offload/delete) after executing each sample's command on a copy of the mirror; entailment refinement only for edits. Correlate trial SE with accuracy, partial on pressure, within model. Go to a Kossen-style SE probe if partial |ρ| ≥ 0.3 (CI excl. 0) or harmful-edit AUROC ≥ 0.65. Plan: `.agent/instruction-semantic-entropy.md`.
Entropy reported in bits (user). Replay = resend the logged request (the model's full input); mirror for executing samples = `render_editable(logged_messages, protect=2)`; offload dir rebuilt by re-running logged commands only when a sample reads it.

## 2026-11-15 09:24 UTC — 9B-RL split across both GPUs
62 concurrent 9B-RL trials on GPU0 ran at about half the per-trial speed of the 4B/9B batches (~30 ops in 20 min, which would put L12800 at ~3 h), while GPU1 was idle after the 9B finished. The 9B server was stopped, a second 9B-RL server (same pinned weights) started on GPU1 :8010, and the 16 LogTriage L12800 + L6400 trials (~30 ops in) were aborted on GPU0 and restarted from scratch on GPU1 (`infra/m5_rl_split.sh`, queue `runs/queues/m5-9b-rl-b.txt`). Aborted attempts are kept in `runs/m5-9b-rl-aborted/` and are not counted. Smoke gate passed first: KV R260 s42 and LT L320 s42 both 1.0, 59/59 calls with parsed tool calls.
SE collection build plan merged into `.agent/instruction-semantic-entropy.md` (Part 1). Disk state rebuilt by replaying logged commands with a per-turn output check; snapshot before each decision point; 10 samples run on snapshot copies. Outcome classes stay/edit/offload/delete + clobber flag, plus invalid / no_command. Labeller gated by self-consistency on the logged command.

## 2026-11-15 13:20 UTC — M5 skill=none arm (4 seeds, 4B / 9B / 9B-RL)
User: run `skill=none` for all three models, 4 seeds, all 8 KV + LogTriage levels, separate plot, in the M5 report. Seeds 42–45; for 4B / 9B at R260 and L320 use 43–46, because M2's seed-42 `none` trials there were not proxied (no LM log, unusable for M6 semantic entropy) and existing seeds are not rerun. 92 trials, all LM-logged to `runs/m5-lmlog/` with tags `m5n-<model>__<task>` (`infra/m5_none_launch.sh`). Old pod could not restart (host out of GPUs); a new 2×A40 pod in EU-SE-1 is created when available. Rootfs pinned to M5's digest (`pull_rootfs.py` now takes a digest) so the M5 and `none` trials replay on the same sandbox.

## 2026-11-15 15:55 UTC — skill=none on 1×A40; 9B LM timeouts, lower concurrency
User switched to 1×A40 (no 2×A40 free; RTX 4090 rejected: 24 GB too small for the 9B, and not in EU-SE-1 where the volume is). Pod `f9a3dd720awllw`, $0.59/h, 4B → 9B → 9B-RL in turn. Without the skill every trial fills the 32k budget, so 32 concurrent 9B trials overflowed the KV cache (143 preemptions) and 10 9B KV trials died on litellm request timeouts (infra, not model). `infra/m5_none_resume.sh` replaces the rest of the launch script: failed attempts moved to `runs/m5n-9b-failed/` (not counted), rerun at N=10; 9B-RL at N=16. Concurrency only, sampling unchanged. 4B: 32/32 budget wall, mean reward 0.00.

## 2026-11-16 — M6 turn labels renamed
User: `logged_edit: bool` replaced by `turn_type` = `context_edit_turn` (harness note "edit applied" in the tool result) or `context_stay_turn` (otherwise). Point selection = all `context_edit_turn`s + 20 fill-stratified `context_stay_turn`s; the label is carried into the Step 8 per-point output.

## 2026-11-16 — M6 pod: 1×A40, 9B only
User: M6 runs on the 9B only; 9B-RL only after 9B results are reported. Separate pod (the M5 `none` pod is stopped by its own session). GPU cap $1.5/h. L40S rejected: not offered in EU-SE-1 (volume region) and ~1.5× speed for 1.85× price; RTX A6000 ~same speed as A40 for +$0.10/h. Pod `obvrywyztadwv4` (`clm-m6-se`), 1×A40, $0.59/h, EU-SE-1, volume `hri0q37of4`; `setup_pod.sh` done, rootfs digest `sha256:05a994d2…` matches M5. Estimate: ~2–4 A40-h of GPU for 9B (sampling ~15k generations, ~200 output tokens each, measured from logs).

## 2026-11-16 — M5B planned: Llama 3.1 8B + Gemma 3 on the M5 sweep (awaiting confirmation)
User: same KV + LogTriage evaluation on Llama-3.1-8B-Instruct and Gemma 3 4B, `clm` at 4 seeds, `none` smoke at 2 seeds (extend to 4 unless mostly 0 with almost no edits); Gemma fallback 3 12B then 2 9B if no decline; Llama fallback the base 8B; new 2×A6000 pod (one GPU per family) on the same volume; routine monitor. Plan and decision rules: `.agent/instruction-m5b.md`. Flagged before running: all four models are gated (no HF token in `.env`); Gemma 2 9B has an 8k context (below the 32k budget); Llama base has no chat/tool format; no thinking mode on these models.

## 2026-11-16 — M6 milestones 1–2 (entropy.py, Pass 1 replay, Gate A)
- `infra/semantic_entropy/entropy.py`: SE, weighted SE, outcome key, clustering, `label_blocks`; imports the harness `_HEADER_RE`. Self-check passes.
- `infra/semantic_entropy/collect.py` subcommands `turns/replay/points/sample/execute`. Sandbox built through harbor's own objects (`Task`, `ChrootEnvironment.start`, `ClmStream.setup`, `cb_setup`), roots on the container disk (`/root/m6roots`), not the volume.
- **Turn loader fix:** the proxy writes lines at completion, so a slow retried call lands after its retry (`kv-store-R4000-seed46`, a 10-min call). Lines are sorted by `t0`; a call "ran" iff any later request has its `tool_call_id`. Kept turns = timing-log bash steps − 1 (the last call has no next request to check against) on all 4 dev trials.
- Status names: no-tool-call samples are keyed `no_tool_call` (plan: `no_command`), `context_status` as is; harness exceptions during a sample → `error`.
- Data files for clobber = everything under `/tmp` and `/app` except `/tmp/.live_ctx` and `/tmp/.bash_ctx_state` (plan: `/tmp` only; `/app` added since the task workdir is `/app`).
- Dev trials (9B): KV R4000 s46 (wall, 0.125) / s49 (1.0); LogTriage L1600 s49 (wall, 0) / s47 (1.0).
- **Gate A: pass.** 4/4 trials, 432/432 turns byte-identical tool results (no divergence, no note-only mismatches). Rootfs digest matches M5.
