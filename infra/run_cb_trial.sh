#!/usr/bin/env bash
# Run one ContextBench trial with ClmStream on Qwen3.5-4B in the chroot sandbox.
# Env: MODEL (served name, default qwen35-4b), SKILL (none|clm, default none).
# Usage: infra/run_cb_trial.sh <task-name> <trials-dir> [extra harbor args...]
# Settings: App. F no-skill (skill=none, budget 32000, reserve 4096, 240 steps),
# everything else from ClmStream.PAPER_KWARGS.
set -euo pipefail
ROOT=/workspace/apart-epistemics
TASK=$1; TRIALS_DIR=$2; shift 2
source /root/envs/clm-env/bin/activate
export PYTHONPATH=$ROOT/infra${PYTHONPATH:+:$PYTHONPATH}
export OPENAI_API_KEY=EMPTY
mkdir -p "$TRIALS_DIR"
exec harbor trials start \
  -p "$ROOT/data/cb_tasks/$TASK" \
  --trials-dir "$TRIALS_DIR" --trial-name "$TASK" \
  -e chroot_env:ChrootEnvironment \
  -a clm_contextbench:ClmStream -m "openai/${MODEL:-qwen35-4b}" \
  --agent-kwarg api_base=http://localhost:8000/v1 \
  --agent-kwarg "skill=${SKILL:-none}" \
  --agent-kwarg context_budget_tokens=32000 \
  --agent-kwarg context_budget_reserve_tokens=4096 \
  --agent-kwarg max_steps=240 \
  "$@"
