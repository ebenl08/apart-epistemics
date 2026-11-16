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

## 2026-11-16 18:40 UTC — M5B launched (Gemma side) on a 1×A40 pod
User: drop Gemma 2 9B (8k context) and the Llama base fallback; Gemma chain is 3 4B → 3 12B. Two 1×GPU pods instead of one 2×A6000 (Llama access was pending). No A6000 free in secure cloud (API: availability NONE; the regional listing said LOW); user approved A40. Pod `sim3ebk6y0yoaw` (1×A40, EU-SE-1, $0.59/h, volume hri0q37of4) runs `infra/m5b_launch.sh gemma`. Models pinned: gemma-3-4b-it @ 093f9f38, gemma-3-12b-it @ 96b6f1ec, Llama-3.1-8B-Instruct @ 0e9e39f2 (access approved 18:34 UTC; its pod is not created yet). Tool calls via vLLM `pythonic` / `llama3_json` with the v0.33.0 tool templates (`infra/chat_templates/`). OpenRouter considered as an alternative (no GPU needed; Gemma 3 4B has no tool-call provider there); not chosen yet.

## 2026-11-16 18:50 UTC — M5B smoke gate failed for Gemma 3 4B and Llama 3.1 8B
Both models answer with a fenced ```bash block (Llama: "THOUGHT: … ```bash … ```") instead of a native tool call, so vLLM's `pythonic` / `llama3_json` parsers find nothing and the harness only replies "(No tool call in your last turn…)"; both stuck at op 1. Gemma also gets 400s from its template ("Conversation roles must alternate") because the harness sends system, user, user. Smoke trials killed per the gate rule; launch scripts exited at `SMOKE_GATE_FAILED`; both pods still up (vLLM servers loaded). Awaiting user decision on a fix (fenced-bash → tool-call parser; Gemma template that merges consecutive same-role turns).

## 2026-11-16 — M6 milestones 3–4 (Pass 2/3 on dev), full 9B run started
- Pass 2: logged request body resent with `n=10, logprobs=True, seed=sha256(trial:t)`; prompt tokens equal the logged ones at every point. Sent to vLLM `:8010` directly (not through the proxy).
- Pass 3: each sample runs through a fresh `ClmStream`'s `ContextEnv.step` on an rsync copy of the turn-t root (`/root/m6roots/work`); "written" files = mtime ≥ a `.se_marker` touched after the copy. Sampled vLLM messages get `reasoning` → `reasoning_content` before `step` (the harness format).
- **Gate B: 160/160** on the 4 dev trials. 10/10 hand-checked labels correct. Dev SE: 57–93% of points at 0, max 1.57 bits; high-SE points mix offload-now vs answer/lookup-first vs different cut sets.
- Full run: queue `runs/m6-se/queue-9b.txt` (42 `m5-9b` logs), `CONC=16` points per batch (dev 8; KV cache was at 4%), execute 6 in parallel. Two trials diverge in Pass 1 on `ls -la /tmp` metadata only; points after the divergence dropped per plan (not overridden).
- New scripts: `m6_run.sh` (driver: replay → points → sample ∥ execute), `m6_status.sh` (checklist), `analyze.py` (Part 2). scipy / statsmodels / scikit-learn installed in the pod's clm-env for the analysis.

## 2026-11-16 ~20:45 UTC — M6 full 9B run done; Part 2 = GO
- Full run: 42/42 trials, 1409 points, Gate B 1397/1397, 0 errors. A second reverse-order sampler was added to keep the GPU busy between trials; at concurrency 16 it caused 68 vLLM preemptions, restarted at 6 (no more). vLLM stopped after sampling.
- **Part 2 (pre-registered): partial Spearman ρ(mean SE, reward | level) = −0.587 [−0.775, −0.282] → GO.** Harmful-edit proxy AUROC 0.38 is not evidence against: the proxy marks 92% of edit turns as harmful (the recipe always deletes old command turns); plan's ground-truth label not built.
- Analysis env: tabulate added to clm-env. Part 3 extraction runs in vllm-env with `flash-linear-attention` installed (torch unchanged, 2.14.0); `causal_conv1d` not installed (reference PyTorch path, slower). Tool-call arguments converted from JSON strings to dicts before templating, as vLLM does; prompt token counts then equal the logged ones (0 mismatches). Activations captured with forward hooks on each decoder layer (residual stream after the layer) at TBG and SLT, not `output_hidden_states` (memory).

## 2026-11-16 ~22:45 UTC — M6 Part 3 (9B probes) done; pod stopped
- Extraction 42/42 trials, 0 token mismatches; fit on CPU in vllm-env (scikit-learn added there). `probe.py` uses `.to("cuda")` (no `accelerate`) and parses tool-call argument strings into dicts before templating; requests dumped in clm-env first (vllm-env has no harbor/litellm).
- Result: TBG probe AUROC 0.741 for SE > γ* (γ* = 0), Spearman 0.466; controls fill+turn 0.578 / 0.159, shuffled 0.483 / −0.033; SE residualized on fill 0.371. SLT weaker (0.648 / 0.331). H2 supported.
- Logistic direction vs diff-of-means at layer 20: cos 0.09; both saved for H3.
- Pod `obvrywyztadwv4` stopped (API v2 action stop). Volume keeps all outputs. 9B-RL not started: waits for the user after this report.

## 2026-11-16 — M6 9B-RL launched (unattended chain)
- User: should have run 9B-RL overnight without waiting; report tables in chat. Old pod `obvrywyztadwv4` could not restart (no free GPU on its host); new pod `i2qg43j6zshuor` (`clm-m6-se-rl`, 1×A40, $0.59/h, EU-SE-1, same volume). Old pod left stopped (not terminated).
- Same protocol as 9B. Control: the same 42 cells/seeds (`queue-9b.txt` with prefix `m5-9b-rl`), K = 10, point rule, outcome key, sampling params from the logged requests. Vary: model = 9B-RL `rl-ckpt-livectx_dapo-iter44` @ ffc4aab2 served as `qwen35-9b-rl` (M5 flags), on :8010. Sampler `CONC=20`, single forward sampler (no reverse sampler).
- New: `infra/semantic_entropy/m6_chain.sh` (serve → m6_run → analyze → probe dump/extract/fit), `m6env.sh` now in the repo (was pod-only), `probe.py` reads the weights path from `M6_MODEL`.

## 2026-11-16 01:22 UTC — M5B pods stopped; fix approved in principle
The two M5B pods sat idle with vLLM loaded from the gate failure (~18:45 UTC on 2026-11-15; the two M5B headings above should read 2026-11-15) until 01:22: ~6.7 h each, ~$8. Both are now stopped. Rule: stop pods whenever work halts. User: fix the format problem (fenced-bash → `bash` tool-call fallback parser, plus the Gemma same-role merge); config not yet confirmed. Optional Qwen 9B text-path control: 1 seed × 16 cells, ~45–60 min. Handoff: `.agent/handoff/handoff-m5b.md`.
- 01:45 UTC: first vLLM start died silently during the flashinfer JIT build (no error, no OOM record; log kept as `runs/logs/vllm-m6-9brl.try1.log`). Relaunched by hand with the same flags; up at ~01:50, chain continued.

## 2026-11-16 — M5B fence parser built (local; not yet run)
- User: one 2×A40 pod for both families (Gemma GPU 0 :8000/proxy :9000, Llama GPU 1 :8010/proxy :9010; 8001 is RunPod nginx). M6 later runs on these models, so the action format must replay exactly.
- `infra/fence_tool_parser.py` (vLLM `--tool-parser-plugin`, parsers `llama3_json_fence` / `pythonic_fence`). It parses the last ```bash/sh/shell block first and falls back to the native parser only when there is none. Fence first because Llama's native parser json-decodes any `{` in the reply. `content` = the text before the block; the call id is `fence_<hex>`. Every reply is logged as `FENCE kind=fallback|native|miss` with the reason, block count and dropped trailing chars. Streaming goes to the native parser only (harness and M6 are non-streaming). No structural tags.
- Templates patched: a `fence_` call replays as `content + "```bash\n" + cmd + "\n```"` (= the generated text), so the budget's token count, the context mirror and the M6 prompt checks match Qwen's message shape. Gemma: alternation check removed, consecutive same-role turns merged (the harness sends system, user, user). Llama: date fixed at 26 Jul 2024 (was `strftime_now`) so replays on another day match.
- Self-check `python3 infra/fence_tool_parser.py` passes (parsing and template round trip, string level). Token-level check and smoke gate still to do on the pod.
- Deviation to report: Llama/Gemma use text-parsed actions, Qwen native calls. `probe.py` changes handed to the M6 session: `.agent/handoff/handoff-m6-probe-nonqwen.md`.

## 2026-11-16 ~02:35 UTC — M5B smoke on 2×A40 pod `ozaojga0i4g45e`; pod stopped
- Try 1 (02:09): every turn after the first got HTTP 400 ("can only concatenate list to list"): vLLM passed `content` as a list of parts to the patched templates. Gemma also wrote bare ``` fences, which the parser rejected. Llama passed the ≥10-calls gate anyway and started the full run; the run was killed. Data moved to `runs/m5b-try1-20261116/`.
- Fixes: `--chat-template-content-format string`; bare fences accepted; the fence language is carried in the call id (`fence_<lang>_<hex>`) so replay stays exact; `SMOKE_ONLY=1` stops a chain after the gate.
- Try 2 (smoke only), 0 HTTP 400s:
  - Llama: 89 calls parsed, 13 misses; KV R260 reward 0.42, LT L320 0.
  - Gemma 4B: KV R260 reward 0 (2 calls, then copies the mirror's `bash {"command": …}` notation and loops for ~460 turns); LT L320 reward 0.
- Llama misses are mostly ```` ```python ```` fences around a `python3 - <<'PY'` heredoc. Waiting for the user to decide on widening the parser.

## 2026-11-16 ~03:10 UTC — M5B models swapped to native tool callers
- User: replace Gemma 3 with **Gemma 4 E4B** (`google/gemma-4-E4B-it` @ 4ecc2ba6; vLLM `gemma4` tool + reasoning parsers, vLLM's `tool_chat_template_gemma4.jinja`, thinking on since the harness sends `enable_thinking`). Replace Llama 3.1 8B with **Ministral 3 8B Instruct 2512** (BF16 repo @ f6fae979; `mistral` parser, `--tokenizer-mode/config-format/load-format mistral`; no thinking). The user chose 2512 over 2410. Both are ungated and use native tool calls, so no fence parser. No Gemma fallback chain.
- Why: the harness's only action is the native `bash` tool. Llama 3.1 and Gemma 3 wrote text (THOUGHT + fences, or the mirror's `bash {…}` notation). Making them work needed a text parser, which is a format deviation from Qwen.
- Deviations to report: the model set differs from the plan; Ministral has no thinking.
- Old 2×A40 pod `ozaojga0i4g45e` could not restart (no free GPUs on its host); new pod `090hikvwfs22gk` (2×A40, $1.18/h). Try-2 data moved to `runs/m5b-try2-20261116/`. The M6 non-Qwen probe handoff was archived at the user's request.

## 2026-11-16 ~04:00 UTC — M5B on pod `090hikvwfs22gk`: both smoke gates passed, `clm` running
- Gemma 4 E4B: smoke gate passed with 169 native calls (KV R260 reward 0, 0/24 answered). `clm` started 03:45.
- Ministral 3 8B needed three fixes, then passed with 161 calls (smoke KV R260 1.0, LT L320 0.96). `clm` started 03:59. The fixes:
  1. The harness's `chat_template_kwargs` get a 400 in Mistral tokenizer mode, so `run_cb_trial.sh` sends `send_chat_template_kwargs=false` for `ministral*` (it has no thinking).
  2. mistral-common 1.13 changed `get_lark_from_jinja` (new required `force_tool_names`), which vLLM 0.33.0 doesn't pass. Pinned `mistral-common==1.12.0` (pod + `setup_pod.sh`).
  3. mistral-common rejects an assistant turn with empty content and no tool call, which the harness sends after an empty reply. The first `clm` attempt lost 10/30 trials to this. `lm_log_proxy.py` now drops those turns before forwarding, for `ministral*` only. The log keeps the request as sent, plus `dropped_empty_assistant`.
- **Deviation to report:** Ministral doesn't see its own empty replies in context (Qwen and Gemma do). M6 replay on Ministral must drop them too.
- Failed data on the volume: `runs/m5b-ministral-try{1,2,3}-20261116/`. Try 3 includes a stray `none` run that the killed chain started at 03:47.

## 2026-11-16 ~11:55 UTC+8 (03:55 UTC) — H3 (decision level) designed and queued
User: after 9B-RL, update `m6-se-paper.md` / `m6-se-results.md`, then run steering or directional ablation.
- Method: **directional ablation by weight orthogonalization** (Arditi et al. 2024, arXiv 2406.11717): W ← (I − d dᵀ) W for every residual-stream writer (embed_tokens, linear_attn.out_proj, self_attn.o_proj, mlp.down_proj; 65 matrices), so the edited model is a plain checkpoint served by vLLM. Chosen over additive steering because vLLM cannot add a vector to the residual stream without code changes, and HF generation is too slow here (no causal_conv1d).
- Control: 9B base, the same 1409 decision points (replay/points copied from `runs/m6-se`), same per-point sampling seeds, K = 10, same labeller and SE. Baseline = the existing 9B SE.
- Vary: model weights. `dom` = unit diff-of-means SE direction at TBG layer 20 (from `direction-m5-9b.npz`); `rand` = random unit direction (seed 0), same procedure (damage control).
- Readouts: paired ΔSE per point (Wilcoxon) and per trial (bootstrap CI); shares of invalid / no_tool_call / error samples (to tell "less uncertain" from "broken"); agreement with the logged decision. Sanity: |h·d|/|h| per layer before/after on one prompt.
- Not yet: task-level reward under ablation (full ContextBench trials, the stated H3 accuracy test). Decide after the decision-level result.
- Code: `ablate.py`, `h3_chain.sh`, `h3_analyze.py`; `collect.py`/`m6_run.sh`/`m6_status.sh` take `M6_OUT`. Outputs `runs/m6-h3/{dom,rand}/`, `runs/m6-h3/h3-decision.md`.
- ~13:00 UTC+8: H3 gate relaxed (waits for the 9B-RL GPU stages only, not its CPU probe fit). User approved a second 1×A40 (`rckduvamr1vclf`, `clm-m6-h3-rand`, $0.59/h, same volume): pod 1 (`i2qg43j6zshuor`) runs `dom`, pod 2 runs `rand`, in parallel. `h3_chain.sh` takes the condition list; logs `runs/logs/h3-chain-{dom,rand}.log`. Why DoM, not the probe weights, is the intervention direction: the probe validates decodability (H2) and picks the layer; regularized LR weights on standardized features favour discriminative low-variance dimensions, and mass-mean directions are more causally implicated (Marks & Tegmark 2023, arXiv 2310.06824); cos(w, DoM) = 0.09 here.
- ~13:10 UTC+8: both H3 chains first stopped at "BASE WEIGHTS MISSING": the weights were complete (19 GB), but `hf download` prints `  path: <dir>` and the script took the whole line as the path. Fixed (`snapshot_download` returns the path; size check > 15 GB) and relaunched both; ~10 min lost.

## 2026-11-16 ~04:30–05:15 UTC — network volume stalls; LM logs moved to local disk
- The RunPod volume (`hri0q37of4`, MooseFS) stalled at times on large writes and on single files. Both logging proxies froze, because each one wrote its log inside its only request loop. GPUs sat idle for ~40 min before the user noticed: the monitor watched only log lines. The 9010 proxy is stuck for good in an uninterruptible wait (`D` state), so Ministral moved to proxy port 9020 (`PROXY` override in `m5b_launch.sh`).
- Lost to it: 5 Gemma `clm` trials ("Connection error"; LT L6400 s43–45, LT L12800 s44–45) and the Ministral smoke trial LT L320 s42 (stuck in volume I/O). The chain was let past it, and its gate passed on the logged calls. All 6 get rerun with the same seeds, since they never completed.
- Fixes: `lm_log_proxy.py` writes in a thread and falls back to `/root/lmlog-fallback` on an I/O error. User: LM logs now go to local disk (`/root/m5-lmlog`), and `infra/lmlog_flush.sh` appends them to `runs/m5-lmlog` when a chain exits (trap). The proxies of the running chains were restarted onto local disk at ~05:10. Those chains use the old launcher, so their logs must be flushed by hand when they finish. Trial dirs are still on the volume.
- Monitoring: anomaly monitor (proxy health, GPU idle with trials in flight, LM-log age, exceptions, chain down, health-check timeout = volume stall), plus a report every 15 min.
- ~13:45 UTC+8: 9B-RL probe fit done. `m6-se-results.md` and `m6-se-paper.md` updated with 9B-RL (Part 2, robustness, probes) and H3 design. Correction: the 9B "first half" result (p = 0.03) holds only when controlling for first-half fill; with whole-trial fill p = 0.18. Paper and notes now call it weak evidence. 9B-RL shows no early signal.
- ~13:55 UTC+8: early H3 peek (1 dom trial, 5 rand trials): dom ablation makes 27% of samples skip the tool call (command written as text / fenced block), which inflates SE. Added "SE over valid samples only" (status keys dropped, ≥ 2 valid samples) to `h3_analyze.py` with its own paired test, to separate a less consistent choice from a broken format. Preliminary: dom ΔSE +0.61 all samples, +0.21 valid-only (p = 0.015, 1 trial); rand ≈ 0.
- ~14:00 UTC+8: dom sampling ~3 points/min vs rand ~9 (≈8 h for dom). Cause: ~4% of dom samples hit the 8192-token cap (rand 0.1%), and the forward sampler does one trial at a time, so stragglers idle the GPU (24 seqs running, KV 30%). Added `m6_rev.sh` (reverse-order second sampler, RCONC 10, same seeds) on both pods. Results unchanged.
- ~14:25 UTC+8: progress dom 191/1409 points (~3.8/min → ~19:40), rand 757/1409 (~15/min → ~15:05). vLLM preemptions since the second samplers: dom 30, rand 83 (recompute only; samples unchanged). Queued `h3_help.sh rand dom` on pod 2: after rand finishes it rebuilds the dom weights (deterministic) and samples dom trials from the middle of the queue forward (same seeds); pod 1 executes them. Expected dom finish ~17:30 instead of ~19:40; no extra GPU.

## 2026-11-16 15:00 UTC+8 — Ministral `none` stage skipped (user, cost)
- The user cut Ministral 3 8B's `skill=none` stage to save cost. Its launcher was killed; the `clm` queue and server kept running. `/root/mistral_finish.sh` on the pod waits for `clm`, runs the trend test, stops the server and flushes the logs. Gemma 4 E4B keeps its `none` data (16/16, all 0).
- Ministral smoke LT L320 s42: the 0.0 is genuine (context budget exhausted, `budget_stop`), not an outage artifact. No rerun.
- ~15:00 UTC+8: user: run only 2 trials per family × level, full λ, and try λ = 0.5 if formatting issues persist. Full `dom` run stopped at 9 executed trials (kept). Subset `queue-h3sub.txt` (16 trials): KV R260 s44–45, R1000 s46–47, R4000 s46–47, R16000 s46–47; LT L320 s44–45, L1600 s44–45, L6400 s48–49, L12800 s44–45 (reuses 6 finished dom trials). Trigger for λ = 0.5 already met (44% format failures at λ = 0 vs 0.2% baseline), so λ = 0.5 (`dom05`) is queued on pod 2 after `rand`.
- Rejection sampling (`collect.py topup`): add samples with new seeds until 10 valid tool calls per point (cap 40); first 10 samples unchanged. Format failures rejected (no_tool_call, context_status, error); `invalid` (non-zero exit) kept as a decision. Outputs `runs/m6-h3/<cond>-rs/`. Baseline not topped up (0.2% failures): its rs-SE uses the valid calls among its 10.
- `h3_analyze.py` now reports SE plain (first 10), valid-only, rejection-sampled; `H3_QUEUE` restricts to the subset. Driver `h3_sub.sh` (pod 1: dom λ = 0 reusing the running vLLM; pod 2: dom05 after rand). `h3_help.sh` cancelled.

## 2026-11-16 15:35 UTC+8 — M5B done: neither Gemma 4 E4B nor Ministral 3 8B shows Qwen's decreasing trend
- Gemma 4 E4B `clm`, 32/32 trials (5 outage trials rerun with the same seeds at 14:23–15:16 UTC+8, archived originals in `runs/m5b-gemma4-outage-20261116/`). Cochran–Armitage trend test, decreasing, on the success rule in `cb_rules.py`: KV 4/16, p = 0.50; LT 3/16, p = 0.34. NOT_DECREASING. Weak at every pressure level. `none`: 16/16 zero, 0 edits, so seeds 44–45 were not added.
- Ministral 3 8B `clm`, 30/30 + 2 smoke: KV 8/16, p = 0.19; LT 1/16, p = 0.88 (z = +1.19; the one LT success is at L12800). NOT_DECREASING. KV is strong to R4000 and weak at R16000 by eye, but the test isn't significant with 4 seeds. LT is near 0 from L1600 on, and L320 only gets partial credit. `none` skipped (user, cost).
- Pod `090hikvwfs22gk` to be stopped. LM logs flushed from `/root/m5-lmlog` to `runs/m5-lmlog`.
- ~16:15 UTC+8: λ = 0.5 (`dom05`) done on the 16-trial subset: format failures 0.1%, ΔSE −0.048 (Wilcoxon p = 0.004), valid-only −0.062 (p = 0.0001); LogTriage down at all levels, KV slightly up. `rand` on the subset flat. Rejection-sampling stage of `h3_sub.sh` was a no-op (`m6env.sh` overwrites `$R`); new `h3_rs.sh` does it, run on pod 2 for `dom` (λ = 0) as pod 1 finishes each trial. `dom05` not topped up (0.1% failures; rs-SE uses its valid calls). `h3_analyze.py` skips empty conditions.
- ~16:35 UTC+8: pod 1 under-used (2 straggling plain trials, KV 47%) while pod 2 rs was saturated (KV 98%). Detached pod 1's `h3_sub.sh dom` parent (its broken rs stage would have stopped vLLM; samplers keep running) and started `h3_rs_rev.sh dom` on pod 1: reverse-order rejection-sampling worker with mkdir claims; overlap with pod 2's forward worker is harmless (topup no-op once 10 valid, execute skips existing). Pod 1 vLLM must be stopped by hand at the end.
- ~17:30 UTC+8: contamination check (user): H1/H2 recomputed with decision-only SE (ok samples only) and status-only SE. H1 holds (9B ρ −0.50 [−0.73, −0.12]; RL −0.45 [−0.70, −0.06]); H2 holds (decision-only AUROC 0.77 / 0.81 vs fill+turn 0.52 / 0.49). In the 9B, status (command/format) uncertainty also predicts reward independently. Clean-direction H3 plan drafted in `instruction-h3-clean.md` (not approved yet).
- ~17:35 UTC+8: user: stop λ = 0 rejection sampling once 8 trials are topped up, or at 17:45 UTC+8 if still at 2. Background watcher on the laptop runs `stop_rs.sh` on both pods (kills workers and in-progress topups, lets executes of topped trials finish, then stops vLLM). Pods stay up pending approval of `instruction-h3-clean.md`.
- ~18:30 UTC+8: λ = 0 rejection sampling stopped at 9 topped trials (watcher misfired at 17:53 because the local network dropped and the SSH count read as 0; stop commands could not reach the pods, so runs continued; stopped by hand at 18:12 when count was 9 ≥ 8). Stop script bug: empty session id when a process exits mid-loop (harmless). One topped trial (L320 s45) was killed before execute and executed separately; L1600 s44 executed twice (identical output). Final H3 numbers in results notes, paper §8 and `handoff-m6-causality.md`. Pod 2 stopped; pod 1 stays up for the `runs/` copy (rsync; local network dropped twice), then stop. Handoffs: `handoff-m6-paper.md`, `handoff-m6-causality.md`.
- User: paper relabels experiments: Experiment 1 = M5 reimplementation eliciting the pressure drop (M5 only, no M5B); Experiment 2 = correlation (H1); Experiment 3 = decodability (H2). Recorded in `handoff-m6-paper.md` and a note at the top of `m6-se-paper.md`.
- ~18:45 UTC+8: `runs/` copied to the laptop (`runs/`, gitignored): 55,937 files, 7.92 GB, identical counts and bytes on both sides (volume `du` said 12 GB: block overhead). Pod 1 stopped; all three M6 pods stopped.
- Decision-only SE methodology recorded: amendment section in `instruction-semantic-entropy.md`, scripts saved as `infra/semantic_entropy/decision_only.py` (h1/h2, as run on the pod), linked from `handoff-m6-paper.md`.
