# Handoff (temporary): CLM reimplementation, M2 / BCP and M5 seed sweep

Session: reimplementation. Updated: 2026-11-15 11:20 UTC (M5 done, committed and pushed; pod stopped).
Plans: [`../instruction-reimplementation.md`](../instruction-reimplementation.md),
[`../instruction-seed-sweep.md`](../instruction-seed-sweep.md) (M5).
Decisions: [`../decisions.md`](../decisions.md).

## Start here (next session)

> **Superseded for the next experiment:** M6 (semantic entropy) starts from
> [`handoff-semantic-entropy.md`](handoff-semantic-entropy.md). It has the current pod state (`f9a3dd720awllw` running the
> `skill=none` 9B-RL arm), RunPod management, and the evidence so far. The notes below describe M5 as of its end.

1. Read this file, then [`../notes/m5-seed-sweep-results.md`](../notes/m5-seed-sweep-results.md) (latest results).
2. **Nothing is running.** M5 pod `ia4u423t1fi61l` (2×A40) is **stopped** (EXITED).
   - Restarting it keeps its container disk: venvs, 4B / 9B / 9B-RL weights, rootfs.
   - Check that 2×A40 are available in EU-SE-1 before relying on a restart.
3. The next step is step 2 of the research plan: uncertainty of the context decisions, using the M5 call logs.
   Another session has drafted M6 (semantic entropy) in `decisions.md`, `instruction-semantic-entropy.md` and
   `instruction-se-collection.md`. Those are uncommitted; coordinate with the user before committing them.

## Where things stand

| Run | Note | Headline |
|---|---|---|
| M2 ContextBench 4B / 9B (2–4 seeds) | [`m2-contextbench-results.md`](../notes/m2-contextbench-results.md) | 4B and 9B fail CLM differently; build-up of the model's own old turns until the budget wall is the common failure |
| M4 BCP 50 q (v3 method text) | [`m2-bcp-results.md`](../notes/m2-bcp-results.md) | 4B 10/50, 9B 12–13/50 |
| **M5 ContextBench seed sweep, 4B / 9B / 9B-RL, 8 seeds per cell** | [`m5-seed-sweep-results.md`](../notes/m5-seed-sweep-results.md) | **The 9B declines with pressure** (trend p ≤ 0.002 on KV and LogTriage); it falls faster than the 4B (model × pressure interaction p = 0.027); budget wall above 0.5x: 4B 9/48, 9B 28/48, 9B-RL 13/48. The RL checkpoint lifts the 9B but keeps its slope |

- M5 used KV + LogTriage only (Needle and Sudoku left out). It ran new seeds only for the 4B and 9B, combined with
  the M2 seeds to make 8 per cell.
- The 9B-RL arm is [`context-language-model/rl-ckpt-livectx_dapo-iter44`](https://huggingface.co/context-language-model/rl-ckpt-livectx_dapo-iter44)
  @ `ffc4aab2f30cb5b802ced6c84e6590ab5fec213d`.
- **Every M5 LM call is logged:** `runs/m5-lmlog/<run>__<task>.jsonl` on the network volume, ~0.7 GB.
  Each line holds the full request plus the response. This is the input for uncertainty replays.
- Four zero-reward trials are answer-format slips, not context failures (listed in the M5 note).

Older M2 per-run notes are in `.agent/notes/archive/`; plots and per-trial tables are in `.agent/notes/figs/`.

## Next steps (open)

1. Step 2: extract uncertainty scores at edit turns from the M5 logs. Contrast budget-wall against successful trials
   and the three models (4B / 9B: different slopes; 9B / 9B-RL: same slope, different level).
2. Optional: the BCP judge (Qwen3.5-27B-GPTQ-Int4), Needle at 8 seeds, no-skill baselines. None were requested.

## Host

**M5 pod `ia4u423t1fi61l`** (stopped):
- RunPod template `mpye6w4gcy`, 2×A40, EU-SE-1, $1.18/h while running.
- Container disk 100 GB (`/`); network volume `hri0q37of4` at `/workspace` (repo, `data/`, `runs/`).
- 96 cores visible, but a cgroup quota of ~16 cores (M5 used ≤ 3); 503 GB RAM.
- SSH: direct only, `ssh -i ~/.ssh/id_ed25519 -p <port> root@<ip>`. The IP and port can change on restart: read them
  from `GET https://api.runpod.io/v2/pods/<id>` (`ssh.direct`). Proxy SSH (`ssh.runpod.io`) rejects the key.
- If the pod is re-created: `nohup infra/setup_pod.sh > runs/logs/setup-pod.log &`.
  - It installs proot, the venvs, the 4B + 9B weights and the rootfs in about 5 min.
  - Download the 9B-RL weights separately (the command is in `instruction-seed-sweep.md`).
- On-disk layout on `/`:
  - venvs `/root/envs/{vllm-env,clm-env,hf}`;
  - weights `/root/hf_cache` (4B, 9B) and `/root/models/clm-9b-rl/converted`;
  - rootfs `/root/rootfs/py312slim`.

**RunPod API:**
- REST v1 was retired 2026-11-15; use v2 (`https://api.runpod.io/v2`).
- The key is in `.env`, wrapped in quotes, so strip them.
- The key cannot use `/exec` (403) or read account SSH keys.

**Other pods on the account:**
- `eben_gpu`, `eben_gpu-migration`: stopped.
- `yuki_gpu`: running; not ours.

## Tools

| Path | What |
|---|---|
| `infra/setup_pod.sh`, `infra/pull_rootfs.py` | rebuild the env on a fresh pod |
| `infra/lm_log_proxy.py` | logging proxy in front of vLLM; trials use `api_base=http://localhost:<proxy>/<tag>/v1` |
| `infra/run_queue.sh` | queue runner; `API_BASE_PREFIX` routes each trial through the proxy with tag `<run>__<task>` |
| `infra/run_cb_trial.sh` | one ContextBench trial; `API_BASE` env overrides the endpoint |
| `infra/serve_qwen35_{4b,9b}.sh` | vLLM servers; `PORT` + `CUDA_VISIBLE_DEVICES` from the environment. **Port 8001 is RunPod's nginx**: use 8000 / 8010 |
| `infra/m5_status.sh` | one-screen status: queues, rewards, GPU / CPU / disk, vLLM preemptions |
| `infra/m5_rl_launch.sh`, `infra/m5_rl_split.sh` | 9B-RL swap, smoke gate and full queue; moving trials to the second GPU |
| `infra/cb_report.py` | per-trial table + reward-vs-pressure plot |

Data (gitignored):
- `data/cb_tasks/` now also has KV R260 s44–49, R1000+ s46–49, and LogTriage s44–49.
  - These are copied from `data/ContextBench/tasks/` (which has seeds 42–49 prebuilt), with the timeout raised from
    14400 to 28800.
- Runs: `runs/m5-{4b,9b,9b-rl}/`; aborted 9B-RL attempts in `runs/m5-9b-rl-aborted/` (not counted).

## Gotchas

- Kill vLLM by pid; never run `pgrep -f` / `pkill -f` with the pattern inside the same shell command (it kills that shell).
  Inside a script file it is safe.
- One A40 handles ~40 concurrent trials of a 4B / 9B with 0 preemptions. At ~60 concurrent 9B trials, per-trial speed
  halved, so split across GPUs.
- Background `nohup ... &` over SSH can keep the SSH session open; use `setsid nohup ... < /dev/null &`.
- `cb_status.py` over SSH can hang for minutes on the network volume; run with `timeout`.
- Harbor/litellm "Provider List" noise and proot "can't chdir" warnings are harmless.
- Saved trajectories lose turns the model edited out; use `runs/m5-lmlog/` for the full per-call context (M5 onward).
