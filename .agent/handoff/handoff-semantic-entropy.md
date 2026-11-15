# Handoff: M6 semantic entropy of CLM context decisions (next session)

Written: 2026-11-15 17:45 UTC by the reimplementation session (M2 → M5).
Plan to execute: [`../instruction-semantic-entropy.md`](../instruction-semantic-entropy.md) (Parts 0–3, Steps 0–10, milestones 0–7).
Decisions log: [`../decisions.md`](../decisions.md). Earlier handoff: [`handoff-reimplementation.md`](handoff-reimplementation.md).

## Why we are doing this

Track 4 question: do a CLM's context edits relate to its epistemic uncertainty?
- Step 1 (done): reproduce CLM on ContextBench and find a model whose context management fails as pressure rises.
- **Step 2 (this session): measure uncertainty at each context decision.** Use discrete semantic entropy (SE) over
  K=10 resampled replies to the logged prompt. Then test whether it predicts failure beyond pressure (H1).
- **Step 3 (this session only if H1 holds): linear probe / direction** for that uncertainty (H2), then steering (H3, later).

## Start here

1. **Nothing is running; every pod of ours is stopped.** The `skill=none` arm finished at 17:39 UTC (96/96 trials, all
   three models), its report is written, and pod `f9a3dd720awllw` was stopped (EXITED) at ~17:41 UTC.
   - Restart it with `POST /v2/pods/f9a3dd720awllw/action {"action":"start"}`. That keeps its container disk: venvs,
     all three models' weights, and the pinned rootfs.
   - If its host has no free GPU (this happened to the old 2×A40 pod), create a fresh 1×A40 pod (below) and run `setup_pod.sh`.
   - Confirm with the user before starting any pod.
2. Read the M5 note (results + `skill=none` section), then the M6 plan.
3. **Unpushed commits:** local `main` is ahead of `origin/main`.
   - The commits are the M6 plan (`0888136`), the merge of `reimplementation-m1`, and the `skill=none` results (`a508adc`).
   - Ask the user before pushing.

## Evidence so far

**Main result (M5, `skill=clm`, 8 seeds per cell):** [`m5-seed-sweep-results.md`](../notes/m5-seed-sweep-results.md), plot `figs/m5-combined.png`.

| | KV R260 → R16000 (mean reward) | LogTriage L320 → L12800 | Trend z (KV / LT) | Budget walls above 0.5x |
|---|---|---|---|---|
| 4B | 0.85 / 0.97 / 0.68 / 0.87 | 0.99 / 0.78 / 0.80 / 0.72 | 0.19 / −1.54 | 9/48 |
| 9B | 0.95 / 0.64 / 0.55 / **0.12** | 0.83 / 0.43 / **0.18** / 0.25 | **−2.84 / −3.27** | **28/48** |
| 9B-RL | 0.99 / 0.88 / 0.57 / 0.38 | 0.87 / 0.74 / 0.77 / 0.60 | −3.07 / −2.04 | 13/48 |

- **The 9B gets worse with pressure; the 4B does not.**
  - Model × log₂ pressure interaction, 9B vs 4B: −0.49 (SE 0.22, p = 0.027).
  - 9B-RL vs 9B: same slope (p = 0.68), higher level.
- **The failure is context management, not retrieval:** the 9B hits the 32k budget wall.
- Four zero-reward trials are answer-format slips. They are listed in the M5 note; exclude them or flag them in M6.

**`skill=none` arm (4 seeds per cell):** same note, plot `figs/m5-none-progress.png`.
- 4B, 9B and 9B-RL: 96/96 trials hit the wall, and 93/96 score 0. The three nonzero trials are all at the lowest level.
  The models made 12 edits in total.
- Progress before the wall falls with pressure at nearly the same rate for all three models. The 9B-RL gets slightly
  further at low pressure.
- The 4B / 9B difference appears only with the method text (`clm`).
- For SE: `none` trials almost never edit, so their SE over edit outcomes will be ~0 by construction. They are a
  baseline, not the main test set.

**Contrasts M6 can test:**
- 4B vs 9B: different slopes.
- 9B vs 9B-RL: same slope, different level.
- Within the 9B: wall vs success at the same level.

## Data for M6 (on the network volume, gitignored)

- **LM call logs:** `runs/m5-lmlog/<run>__<task>.jsonl`, ~0.8 GB. One line per LM call:
  `{"t0","t1","status","request","response"}`, written verbatim by `infra/lm_log_proxy.py`.
  - **Step 0.1 already checked** on `m5-9b__kv-store-R4000-seed46.jsonl`:
    - `request` keys: `chat_template_kwargs, max_tokens, messages, model, temperature, tools, top_p`.
    - `response.usage` has `prompt_tokens`.
    - The message keys are `content, reasoning, role, ...`. **The reasoning field is `reasoning`, not
      `reasoning_content`.** `tool_calls` appears only when a call was made. Adjust plan Step 2 accordingly.

| Run tag | Files | Which trials are logged |
|---|---|---|
| `m5-4b`, `m5-9b` (`clm`) | 42 each | KV R260 s44–49, KV R1000 / R4000 / R16000 s46–49, LogTriage s44–49. **M2 seeds (42–43, KV R1000+ 44–45) were not logged.** |
| `m5-9b-rl` (`clm`) | 64 | all 8 cells × s42–49 (incl. 2 smoke trials) |
| `m5n-4b`, `m5n-9b` (`none`) | 32 each | all cells, s42–45 (R260 / L320: s43–46) |
| `m5n-9b-rl` (`none`) | 32 | all cells, s42–45 |

- **Trial dirs** (rewards, `result.json`, timing logs): `runs/m5-{4b,9b,9b-rl}/trials/`, `runs/m5n-{4b,9b,9b-rl}/trials/`.
- **Not counted:** `runs/m5-9b-rl-aborted/` and `runs/m5n-9b-failed/` (infra aborts and timeouts). Their logs were moved
  there too.
- **Per-trial tables** with reward, ops, edits, peak ctx and end reason: `.agent/notes/figs/m5-combined.md`, `m5-none.md`.
- **Replay sandbox:** M5 rootfs `python:3.12-slim` amd64 digest
  `sha256:05a994d2344eb364cc186910f4fc8786a38215f39f00d0acc25bff33a08f4177`.
  - `infra/setup_pod.sh` now pins it automatically (from `runs/logs/setup-pod.log`).
  - Replay on this digest only.

## RunPod management

**Account and API**
- Key in `.env` (`RUNPOD_API_KEY`), wrapped in quotes: `K=$(grep RUNPOD_API_KEY .env | cut -d= -f2- | tr -d '\r\n "'"'"'")`.
  - **Never print it; never commit `.env`.**
- REST **v2** only (`https://api.runpod.io/v2`, header `Authorization: Bearer $K`); v1 is retired.
  - Status: `GET /v2/pods/<id>` → `status`, `ssh.direct`, `cost`.
  - Stop / start: `POST /v2/pods/<id>/action {"action":"stop"|"start"}`.
  - Create: `POST /v2/pods` with body like
    `{"name","templateId":"mpye6w4gcy","gpu":{"id":"NVIDIA A40","count":1},"dataCenterIds":["EU-SE-1"],"disk":100,"mounts":{"network":[{"volumeId":"hri0q37of4","path":"/workspace"}]},"env":{"PUBLIC_KEY":"<~/.ssh/id_ed25519.pub>"},"ports":["8888/http","22/tcp"]}`.
  - Availability: `GET /v2/catalog/datacenters?include=GPU_AVAILABILITY`. Prices: `GET /v2/catalog/gpus`.
- The key cannot use `/exec` (403). Proxy SSH (`ssh.runpod.io`) rejects our key. **Use direct SSH:**
  `ssh -i ~/.ssh/id_ed25519 -p <port> root@<ip>`, with `ip` and `port` from `ssh.direct`. They change on every new pod or restart.

**Pods**

| Pod | GPU | State (17:45 UTC) | Notes |
|---|---|---|---|
| `f9a3dd720awllw` (`clm-m5-none`) | 1×A40, $0.59/h | stopped 2026-11-15 ~17:41 UTC | Last SSH `root@194.68.245.201 -p 22146` (changes on restart). Container disk has venvs, 4B / 9B / 9B-RL weights, pinned rootfs |
| `ia4u423t1fi61l` (`clm-m5-sweep`) | 2×A40 | stopped | Cannot restart: its host has no free GPUs. Has the same container-disk setup; delete only if the user agrees |
| `yuki_gpu` | | running | **Not ours, never touch** |
| `eben_gpu`, `eben_gpu-migration` | | stopped | old |

**Region and storage**
- The network volume `hri0q37of4` lives in EU-SE-1, so pods that need `data/` and `runs/` must be in EU-SE-1.
- EU-SE-1 offers A40 and RTX A6000, often at LOW availability. 2×A40 was unavailable on 2026-11-15.
- **The RTX 4090 was rejected:** 24 GB is too small for the 9B with 32k contexts, and EU-SE-1 has none.

**Fresh pod**
- `setsid nohup infra/setup_pod.sh > runs/logs/setup-pod-<name>.log 2>&1 < /dev/null &` takes about 5–10 min.
  **Never write to `runs/logs/setup-pod.log`:** it holds the pinned digest.
- 9B-RL weights: `hf download context-language-model/rl-ckpt-livectx_dapo-iter44 --revision ffc4aab2f30cb5b802ced6c84e6590ab5fec213d --include "converted/*" --local-dir /root/models/clm-9b-rl`.
  `infra/m5_none_launch.sh` does it automatically.
- **Repo on the volume:** branch `reimplementation-m1` at `845bfb1`. The newer infra (`run_status.sh`, `m5_none_*.sh`,
  `pull_rootfs.py`, `setup_pod.sh`) was copied over by scp and is not committed there. Local `main` is the source of truth.
- Capacity: 1×A40 has a cgroup quota of ~7.65 CPU cores; the 2×A40 pod had ~16.

**Serving and running**
- **Always `source /root/envs/vllm-env/bin/activate` before `vllm serve`.** Without it torch compile can't find `ninja`
  and the engine dies (this cost 40 min on 2026-11-15).
  - `infra/serve_qwen35_{4b,9b}.sh` take `PORT` and `CUDA_VISIBLE_DEVICES`.
  - **Port 8001 is RunPod's nginx**; use 8000 / 8010.
- **Concurrency limits on one A40** (keep vLLM preemptions at 0):

  | Workload | Safe concurrency |
  |---|---|
  | `clm` trials (small contexts) | ~40 |
  | Full-context `none` 9B trials | ≤ 16 |
  | 4B `none` | 32 |

  - At 32 concurrent 9B `none` trials the KV cache overflowed, and 10 trials died on litellm request timeouts.
  - For M6 sampling (n=10 per prompt, prompts up to ~32k): start at ~8 points per server, as the plan says, and watch preemptions.
- Long jobs: `setsid nohup ... < /dev/null &`. Plain `nohup ... &` keeps the SSH session open.
- Kill vLLM by pid. Never put the pattern of `pgrep -f` / `pkill -f` literally inside an SSH command string: it matches and
  kills the calling shell. Use a bracket trick (`"vllm.serv[e]"`) or a script file.
- macOS here has no `timeout` command.

**Monitoring**
- Status: `infra/run_status.sh <queue names>`. Queue `<q>` is `runs/queues/<q>.txt`, its log is `runs/logs/queue-<q>.log`.
  It prints `[x]/[ ]` per queue with done/total, mean reward, walls, GPU, cgroup CPU, RAM, disk and vLLM running / waiting / preemptions / KV.
- Queue runner: `infra/run_queue.sh <queue> <N>`. Each line is `MODEL SKILL TASK RUN_DIR`.
  `API_BASE_PREFIX=http://localhost:<proxy>` routes each trial through the logging proxy.
- **Watch for three things:** queue milestones, new `exception.txt` files, and the GPU idle for several minutes (a dead server).
  Checking only the log missed a dead vLLM for 40 min.

## User preferences (also in memory)

- **Before running anything,** bullet the config as Control / Vary, highlight the changes, and **wait for the user to confirm**.
- **Do not change the GPU type or count without asking.**
- **Ask before every commit and push.**
- Log decisions in `.agent/decisions.md` and suggest handoff updates.
- Progress reports as a **checklist with done/total plus GPU and CPU utilization**. **Always keep a monitor running**
  until the run ends, and re-arm it after each notification.
- Give only verified links.
- Don't rerun existing seeds; use new ones.
- Weights don't need to persist (they live on the container disk, not the volume).

## Next steps (M6 milestones, from the plan)

| # | Done when | State |
|---|---|---|
| 0 | Log fields confirmed; `lm_log_proxy.py` in `infra/` | **done** (fields above; proxy committed in `845bfb1` / `main`) |
| 1 | `infra/semantic_entropy/entropy.py` self-check passes | todo |
| 2 | Pass 1 (replay) passes Gate A on 2 dev trials (one KV, one LogTriage) | todo, CPU only |
| 3 | Pass 3 passes Gate B; 10 labels hand-checked | todo |
| 4 | SE for the 2 dev trials; distribution and 5 high-SE points read | needs GPU (Step 6 sampling) |
| 5 | Full run on all logged M5 trials; QA report | GPU |
| 6 | Part 2 correlation; go / no-go in `decisions.md` | |
| 7 | (Go) Part 3 probe | |

- **CPU steps (1–3) need the volume:** replay needs the trial logs and the rootfs.
  - Either keep a cheap pod running, or copy 2 dev trials' logs plus the rootfs locally.
  - Proot replay was only ever run on the pod (Linux); this Mac can't run it.
- **Pick dev trials** from the 9B, where SE should vary, e.g. a KV R4000 trial that hit the wall and a LogTriage L1600 one,
  each with a matched successful seed.
- **Risk to check early (plan risk 2):** the 4B with `clm` follows a fixed recipe, so its SE may be ~0 everywhere.
  Look at the SE distribution before scaling up.
