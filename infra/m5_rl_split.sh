#!/usr/bin/env bash
# Move the 16 longest 9B-RL trials (LogTriage L12800 + L6400) from GPU0 to a second 9B-RL server on GPU1.
# They were ~30 ops in; aborted attempts are moved to runs/m5-9b-rl-aborted/ (trial dirs + LM logs).
set -u
cd /workspace/apart-epistemics
for pid in $(pgrep -f "vllm serve Qwen/Qwen3.5-9B"); do kill $pid; done
while nvidia-smi -i 1 --query-gpu=memory.used --format=csv,noheader,nounits | awk '{exit !($1>2000)}'; do sleep 5; done
source /root/envs/vllm-env/bin/activate
CUDA_VISIBLE_DEVICES=1 setsid nohup vllm serve /root/models/clm-9b-rl/converted --served-model-name qwen35-9b-rl \
  --port 8010 --max-model-len 65536 --language-model-only \
  --enable-auto-tool-choice --tool-call-parser qwen3_coder --reasoning-parser qwen3 \
  --gpu-memory-utilization 0.90 --enable-prefix-caching > runs/logs/vllm-m5-9b-rl-gpu1.log 2>&1 < /dev/null &
until curl -sf localhost:8010/v1/models > /dev/null; do sleep 10; done
echo "$(date -u +%T) GPU1 9B-RL up; aborting L12800/L6400 on GPU0"
Q=runs/queues/m5-9b-rl-b.txt; echo "# 9B-RL L12800 + L6400 moved to GPU1" > $Q
mkdir -p runs/m5-9b-rl-aborted
for t in log-triage-L12800-seed{42..49} log-triage-L6400-seed{42..49}; do
  pkill -f "data/cb_tasks/$t --trials-dir /workspace/apart-epistemics/runs/m5-9b-rl/"
  echo "qwen35-9b-rl clm $t /workspace/apart-epistemics/runs/m5-9b-rl" >> $Q
done
sleep 20
for t in log-triage-L12800-seed{42..49} log-triage-L6400-seed{42..49}; do
  mv runs/m5-9b-rl/trials/$t runs/m5-9b-rl-aborted/ 2>/dev/null
  mv runs/m5-lmlog/m5-9b-rl__$t.jsonl runs/m5-9b-rl-aborted/ 2>/dev/null
  mv runs/m5-9b-rl/$t.log runs/m5-9b-rl-aborted/ 2>/dev/null
done
echo "$(date -u +%T) restarting 16 trials on GPU1"
API_BASE_PREFIX=http://localhost:9001 infra/run_queue.sh $Q 16
