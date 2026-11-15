#!/usr/bin/env bash
# Wait for the 4B queue, swap GPU0 to the pinned 9B-RL checkpoint, smoke it, then run its full queue.
# Gate: the smoke trials' LM log must contain parsed tool calls (else stop and leave it for a human).
set -u
cd /workspace/apart-epistemics
until grep -q "QUEUE DONE" runs/logs/queue-m5-4b.log; do sleep 30; done
echo "$(date -u +%T) 4B queue done; swapping GPU0 to 9B-RL"
for pid in $(pgrep -f "vllm serve Qwen/Qwen3.5-4B"); do kill $pid; done
while nvidia-smi -i 0 --query-gpu=memory.used --format=csv,noheader,nounits | awk '{exit !($1>2000)}'; do sleep 5; done
source /root/envs/vllm-env/bin/activate
CUDA_VISIBLE_DEVICES=0 setsid nohup vllm serve /root/models/clm-9b-rl/converted --served-model-name qwen35-9b-rl \
  --port 8000 --max-model-len 65536 --language-model-only \
  --enable-auto-tool-choice --tool-call-parser qwen3_coder --reasoning-parser qwen3 \
  --gpu-memory-utilization 0.90 --enable-prefix-caching > runs/logs/vllm-m5-9b-rl.log 2>&1 < /dev/null &
setsid nohup python infra/lm_log_proxy.py 9002 http://localhost:8000 runs/m5-lmlog > runs/logs/proxy-9002.log 2>&1 < /dev/null &
until curl -sf localhost:8000/v1/models > /dev/null; do sleep 10; done
echo "$(date -u +%T) 9B-RL server up; smoke"
export API_BASE_PREFIX=http://localhost:9002
infra/run_queue.sh runs/queues/m5-9b-rl-smoke.txt 2
n=$(cat runs/m5-lmlog/m5-9b-rl__kv-store-R260-seed42.jsonl runs/m5-lmlog/m5-9b-rl__log-triage-L320-seed42.jsonl 2>/dev/null \
    | grep -c '"tool_calls": \[{')
echo "$(date -u +%T) smoke: $n calls with parsed tool calls"
/root/envs/clm-env/bin/python infra/cb_status.py runs/m5-9b-rl/trials
[ "$n" -ge 10 ] || { echo "SMOKE_GATE_FAILED"; exit 1; }
infra/run_queue.sh runs/queues/m5-9b-rl.txt 64
