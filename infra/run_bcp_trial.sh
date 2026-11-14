#!/usr/bin/env bash
# Run one BrowseComp-Plus trial with ClmAgent (configs/bcp.yaml) in the proot sandbox.
# Usage: infra/run_bcp_trial.sh <query-id> <trials-dir> [extra harbor args...]
# Env: MODEL (served name, default qwen35-4b), BCP_SKILL (bcp_search | bcp_search_clm),
#      BCP_TASKS (bcp_tasks | bcp_tasks_v3: method text in the instruction).
# Needs: vLLM on :8000, infra/bcp/search_server.py on :8100, data/bcp_tasks/bcp-<id>.
# Overrides vs bcp.yaml: cost_metric=usd (bcp.yaml's FLOPs key is for 27B).
set -euo pipefail
ROOT=/workspace/apart-epistemics
QID=$1; TRIALS_DIR=$2; shift 2
source /root/envs/clm-env/bin/activate
export PYTHONPATH=$ROOT/infra${PYTHONPATH:+:$PYTHONPATH}
export API_BASE=http://localhost:8000/v1
export MODEL="openai/${MODEL:-qwen35-4b}"
export HARBOR_ENV=chroot_env:ChrootEnvironment
export TRIALS_DIR
mkdir -p "$TRIALS_DIR"
exec "$ROOT/context-language-models/clm/examples/run_harbor.sh" \
  "$ROOT/data/${BCP_TASKS:-bcp_tasks}/bcp-$QID" bcp \
  --agent-kwarg "skill_dirs=$ROOT/infra/bcp/skill/${BCP_SKILL:-bcp_search}" \
  --agent-kwarg cost_metric=usd \
  --trial-name "bcp-$QID" \
  "$@"
