#!/usr/bin/env bash
# Run a queue of ContextBench trials, at most N at a time, with CB_SETTINGS=paper.
# Queue file: one trial per line, "MODEL SKILL TASK RUN_DIR" (# comments allowed).
# Each trial writes RUN_DIR/trials/<task>/ and logs to RUN_DIR/<task>.log.
# Usage: nohup infra/run_queue.sh <queue-file> [N=16] > <log> 2>&1 &
set -uo pipefail
Q=$1; N=${2:-16}; ROOT=/workspace/apart-epistemics
one() {
  read -r model skill task rundir <<<"$1"
  mkdir -p "$rundir"
  echo "$(date -u +%T) START $model $skill $task"
  [[ -n "${API_BASE_PREFIX:-}" ]] && export API_BASE="$API_BASE_PREFIX/$(basename "$rundir")__$task/v1"
  MODEL=$model SKILL=$skill CB_SETTINGS=paper \
    "$ROOT/infra/run_cb_trial.sh" "$task" "$rundir/trials" > "$rundir/$task.log" 2>&1
  echo "$(date -u +%T) END rc=$? $model $skill $task"
}
export -f one; export ROOT API_BASE_PREFIX
grep -v '^\s*#' "$Q" | grep -v '^\s*$' | xargs -P "$N" -I{} bash -c 'one "$@"' _ {}
echo "$(date -u +%T) QUEUE DONE $Q"
