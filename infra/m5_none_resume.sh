#!/usr/bin/env bash
# Replaces the tail of m5_none_launch.sh after the 9B batch hit LM request timeouts at 32 concurrent
# (no-skill contexts fill the 32k budget, so the KV cache preempted heavily; 4B was unaffected).
# Waits for the 9B queue, reruns its failed trials at N=10, then 9B-RL at N=16. Failed attempts go to runs/m5n-9b-failed/.
# Usage: setsid nohup infra/m5_none_resume.sh [rl-only] > runs/logs/m5-none-resume.log 2>&1 < /dev/null &
set -u
cd /workspace/apart-epistemics
if [[ "${1:-}" != rl-only ]]; then
  until grep -q "QUEUE DONE" runs/logs/queue-m5n-9b.log; do sleep 30; done
  echo "$(date -u +%T) 9B queue done"
  mkdir -p runs/m5n-9b-failed; Q=runs/queues/m5n-9b-retry.txt; echo "# 9B trials that failed on LM timeouts" > $Q
  for d in runs/m5n-9b/trials/*/; do
    t=$(basename $d)
    [[ -f $d/exception.txt ]] || continue
    mv $d runs/m5n-9b-failed/; mv runs/m5n-9b/$t.log runs/m5n-9b-failed/ 2>/dev/null
    mv runs/m5-lmlog/m5n-9b__$t.jsonl runs/m5n-9b-failed/ 2>/dev/null
    echo "qwen35-9b none $t /workspace/apart-epistemics/runs/m5n-9b" >> $Q
  done
  echo "$(date -u +%T) rerunning $(grep -vc '^#' $Q) failed 9B trials at N=10"
  API_BASE_PREFIX=http://localhost:9000 infra/run_queue.sh $Q 10 > runs/logs/queue-m5n-9b-retry.log 2>&1
  echo "$(date -u +%T) 9b retry done"
fi

for pid in $(pgrep -f "vllm serve"); do kill $pid; done
while nvidia-smi -i 0 --query-gpu=memory.used --format=csv,noheader,nounits | awk '{exit !($1>2000)}'; do sleep 5; done
source /root/envs/vllm-env/bin/activate  # torch compile needs the venv's ninja on PATH
CUDA_VISIBLE_DEVICES=0 setsid nohup vllm serve /root/models/clm-9b-rl/converted \
  --served-model-name qwen35-9b-rl --port 8000 --max-model-len 65536 --language-model-only \
  --enable-auto-tool-choice --tool-call-parser qwen3_coder --reasoning-parser qwen3 \
  --gpu-memory-utilization 0.90 --enable-prefix-caching > runs/logs/vllm-m5n-9b-rl.log 2>&1 < /dev/null &
vpid=$!
until curl -sf localhost:8000/v1/models > /dev/null; do
  kill -0 $vpid 2>/dev/null || { echo "$(date -u +%T) VLLM_START_FAILED, see runs/logs/vllm-m5n-9b-rl.log"; exit 1; }
  sleep 10
done
echo "$(date -u +%T) 9b-rl server up"
API_BASE_PREFIX=http://localhost:9000 infra/run_queue.sh runs/queues/m5n-9b-rl.txt 16 > runs/logs/queue-m5n-9b-rl.log 2>&1
echo "$(date -u +%T) 9b-rl queue done"
for pid in $(pgrep -f "vllm serve"); do kill $pid; done
echo "$(date -u +%T) ALL DONE"
