#!/usr/bin/env bash
# M5B on one GPU: smoke gate -> skill=clm (seeds 42-45) -> [Gemma: trend rule, fallback 3 4B -> 3 12B]
# -> skill=none smoke (seeds 42-43) -> none-smoke rule -> [seeds 44-45]. Rules: .agent/instruction-m5b.md.
# Usage: setsid nohup infra/m5b_launch.sh <gemma|llama> > runs/logs/m5b-<family>.log 2>&1 < /dev/null &
set -u
cd /workspace/apart-epistemics
case $1 in gemma) chain=(gemma3-4b gemma3-12b) ;; llama) chain=(llama31-8b) ;; *) echo "unknown family"; exit 2 ;; esac
LEVELS="log-triage-L12800 kv-store-R16000 log-triage-L6400 kv-store-R4000 log-triage-L1600 kv-store-R1000 log-triage-L320 kv-store-R260"
R=/workspace/apart-epistemics/runs
mkdir -p runs/queues runs/logs
say() { echo "$(date -u +%T) $*"; }

queue() {  # queue <name> <model> <skill> <seeds> [skip-smoke]: write runs/queues/<name>.txt
  local q=runs/queues/$1.txt; echo "# M5B $2 $3 seeds $4" > $q
  for t in $LEVELS; do for s in $4; do
    [[ ${5:-} == skip-smoke && $s == 42 && ( $t == kv-store-R260 || $t == log-triage-L320 ) ]] && continue
    echo "$2 $3 $t-seed$s $R/m5b-$2-$3" >> $q
  done; done
}
run() { API_BASE_PREFIX=http://localhost:9000 infra/run_queue.sh runs/queues/$1.txt $2 > runs/logs/queue-$1.log 2>&1
        say "$1 queue done"; }

serve() {  # stop any server on :8000, start <model>, wait until it answers or dies
  for pid in $(pgrep -f "vllm serve"); do kill $pid; done
  while nvidia-smi -i 0 --query-gpu=memory.used --format=csv,noheader,nounits | awk '{exit !($1>2000)}'; do sleep 5; done
  CUDA_VISIBLE_DEVICES=0 PORT=8000 setsid nohup infra/serve_m5b.sh $1 > runs/logs/vllm-m5b-$1.log 2>&1 < /dev/null &
  local vpid=$!
  until curl -sf localhost:8000/v1/models > /dev/null; do
    kill -0 $vpid 2>/dev/null || { say "VLLM_START_FAILED $1, see runs/logs/vllm-m5b-$1.log"; exit 1; }
    sleep 10
  done
  say "$1 server up"
}

setsid nohup /root/envs/clm-env/bin/python infra/lm_log_proxy.py 9000 http://localhost:8000 runs/m5-lmlog \
  > runs/logs/proxy-9000.log 2>&1 < /dev/null &

for m in "${chain[@]}"; do
  serve $m
  queue m5b-$m-smoke $m clm 42
  sed -i '/kv-store-R260-seed42\|log-triage-L320-seed42/!{/^#/!d}' runs/queues/m5b-$m-smoke.txt
  run m5b-$m-smoke 2
  n=$(cat runs/m5-lmlog/m5b-$m-clm__{kv-store-R260,log-triage-L320}-seed42.jsonl 2>/dev/null | grep -c '"tool_calls": \[{')
  say "$m smoke: $n calls with parsed tool calls"
  [[ $n -ge 10 ]] || { say "SMOKE_GATE_FAILED $m"; exit 1; }
  queue m5b-$m-clm $m clm "42 43 44 45" skip-smoke
  run m5b-$m-clm 32
  /root/envs/clm-env/bin/python infra/cb_rules.py trend $R/m5b-$m-clm | sed 's/^/  /'
  if /root/envs/clm-env/bin/python infra/cb_rules.py trend $R/m5b-$m-clm > /dev/null; then
    say "$m DECREASING, stop chain"; break
  fi
  say "$m NOT_DECREASING"
done
final=$m; say "skill=none on $final"

queue m5b-$final-none $final none "42 43"
run m5b-$final-none 16
/root/envs/clm-env/bin/python infra/cb_rules.py none-smoke $R/m5b-$final-none | sed 's/^/  /'
if ! /root/envs/clm-env/bin/python infra/cb_rules.py none-smoke $R/m5b-$final-none > /dev/null; then
  queue m5b-$final-none-b $final none "44 45"
  run m5b-$final-none-b 16
fi
for pid in $(pgrep -f "vllm serve"); do kill $pid; done
say "ALL DONE"
