#!/usr/bin/env bash
# M5 skill=none arm on one GPU: 4B -> 9B -> 9B-RL, each model's trials all at once.
# Seeds 42-45 at all 8 KV / LogTriage levels (4B / 9B R260 + L320: 43-46, since M2 ran an unlogged seed 42 there).
# LM calls are logged to runs/m5-lmlog/ with tags m5n-<model>__<task>.
# Usage: setsid nohup infra/m5_none_launch.sh > runs/logs/m5-none-launch.log 2>&1 < /dev/null &
set -u
cd /workspace/apart-epistemics
R=/workspace/apart-epistemics/runs
mkdir -p runs/queues runs/logs
for m in 4b 9b 9b-rl; do
  Q=runs/queues/m5n-$m.txt; echo "# M5 skill=none, $m, highest pressure first" > $Q
  for t in log-triage-L12800 kv-store-R16000 log-triage-L6400 kv-store-R4000 log-triage-L1600 kv-store-R1000 \
           log-triage-L320 kv-store-R260; do
    seeds="42 43 44 45"
    # M2 smoke grid already ran seed 42 here, unlogged: use 43-46 so all 4 are new and LM-logged
    [[ $m != 9b-rl && ( $t == kv-store-R260 || $t == log-triage-L320 ) ]] && seeds="43 44 45 46"
    for s in $seeds; do
      echo "qwen35-$m none $t-seed$s $R/m5n-$m" >> $Q
    done
  done
done

if [[ ! -d /root/models/clm-9b-rl/converted ]]; then
  ( HF_HUB_ENABLE_HF_TRANSFER=1 /root/envs/hf/bin/hf download context-language-model/rl-ckpt-livectx_dapo-iter44 \
      --revision ffc4aab2f30cb5b802ced6c84e6590ab5fec213d --include "converted/*" --local-dir /root/models/clm-9b-rl
    echo RL_WEIGHTS_DONE ) > runs/logs/hf-9b-rl.log 2>&1 &
fi
setsid nohup /root/envs/clm-env/bin/python infra/lm_log_proxy.py 9000 http://localhost:8000 runs/m5-lmlog \
  > runs/logs/proxy-9000.log 2>&1 < /dev/null &

serve() {  # serve <name> <cmd...>: stop any server on :8000, start this one, wait until it answers
  for pid in $(pgrep -f "vllm serve"); do kill $pid; done
  while nvidia-smi -i 0 --query-gpu=memory.used --format=csv,noheader,nounits | awk '{exit !($1>2000)}'; do sleep 5; done
  local name=$1; shift
  CUDA_VISIBLE_DEVICES=0 PORT=8000 setsid nohup "$@" > runs/logs/vllm-m5n-$name.log 2>&1 < /dev/null &
  until curl -sf localhost:8000/v1/models > /dev/null; do sleep 10; done
  echo "$(date -u +%T) $name server up"
}
run() { API_BASE_PREFIX=http://localhost:9000 infra/run_queue.sh runs/queues/m5n-$1.txt 32 > runs/logs/queue-m5n-$1.log 2>&1
        echo "$(date -u +%T) $1 queue done"; }

serve 4b infra/serve_qwen35_4b.sh; run 4b
serve 9b infra/serve_qwen35_9b.sh; run 9b
until [[ -d /root/models/clm-9b-rl/converted ]] && ! pgrep -f "hf download" > /dev/null; do sleep 10; done
serve 9b-rl /root/envs/vllm-env/bin/vllm serve /root/models/clm-9b-rl/converted --served-model-name qwen35-9b-rl \
  --port 8000 --max-model-len 65536 --language-model-only \
  --enable-auto-tool-choice --tool-call-parser qwen3_coder --reasoning-parser qwen3 \
  --gpu-memory-utilization 0.90 --enable-prefix-caching
run 9b-rl
for pid in $(pgrep -f "vllm serve"); do kill $pid; done
echo "$(date -u +%T) ALL DONE"
