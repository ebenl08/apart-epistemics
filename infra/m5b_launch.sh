#!/usr/bin/env bash
# M5B, one family per GPU of a 2-GPU pod (gemma: Gemma 4 E4B, GPU 0, :8000, proxy :9000;
# mistral: Ministral 3 8B, GPU 1, :8010, proxy :9010). Both use native tool calls.
# Smoke gate -> skill=clm (seeds 42-45) -> trend rule (reported; no fallback model)
# -> skill=none smoke (seeds 42-43) -> none-smoke rule -> [seeds 44-45]. Rules: .agent/instruction-m5b.md.
# Usage: [SMOKE_ONLY=1] setsid nohup infra/m5b_launch.sh <gemma|mistral> > runs/logs/m5b-<family>.log 2>&1 < /dev/null &
set -u
cd /workspace/apart-epistemics
case $1 in gemma) chain=(gemma4-e4b); GPU=0; PORT=8000; PROXY=9000 ;;
  mistral) chain=(ministral3-8b); GPU=1; PORT=8010; PROXY=${PROXY:-9010} ;; *) echo "unknown family"; exit 2 ;; esac
# PROXY=<port> overrides the proxy port (a proxy hung on the volume can keep holding its port)
mine="vllm serve /root/models/($(IFS="|"; echo "${chain[*]}"))"  # never touch the other family's server
LEVELS="log-triage-L12800 kv-store-R16000 log-triage-L6400 kv-store-R4000 log-triage-L1600 kv-store-R1000 log-triage-L320 kv-store-R260"
R=/workspace/apart-epistemics/runs
LMLOG=/root/m5-lmlog  # LM-call logs on local disk (the network volume stalled on 2026-11-16); moved to runs/m5-lmlog at the end
mkdir -p runs/queues runs/logs $LMLOG
trap 'for c in "${chain[@]}"; do infra/lmlog_flush.sh $LMLOG runs/m5-lmlog m5b-$c-; done' EXIT  # also on gate failure
say() { echo "$(date -u +%T) $*"; }

queue() {  # queue <name> <model> <skill> <seeds> [skip-smoke]: write runs/queues/<name>.txt
  local q=runs/queues/$1.txt; echo "# M5B $2 $3 seeds $4" > $q
  for t in $LEVELS; do for s in $4; do
    [[ ${5:-} == skip-smoke && $s == 42 && ( $t == kv-store-R260 || $t == log-triage-L320 ) ]] && continue
    echo "$2 $3 $t-seed$s $R/m5b-$2-$3" >> $q
  done; done
}
run() { API_BASE_PREFIX=http://localhost:$PROXY infra/run_queue.sh runs/queues/$1.txt $2 > runs/logs/queue-$1.log 2>&1
        say "$1 queue done"; }

serve() {  # stop this family's server, start <model> on $GPU:$PORT, wait until it answers or dies
  pkill -f "$mine"
  while nvidia-smi -i $GPU --query-gpu=memory.used --format=csv,noheader,nounits | awk '{exit !($1>2000)}'; do sleep 5; done
  CUDA_VISIBLE_DEVICES=$GPU PORT=$PORT setsid nohup infra/serve_m5b.sh $1 > runs/logs/vllm-m5b-$1.log 2>&1 < /dev/null &
  local vpid=$!
  until curl -sf localhost:$PORT/v1/models > /dev/null; do
    kill -0 $vpid 2>/dev/null || { say "VLLM_START_FAILED $1, see runs/logs/vllm-m5b-$1.log"; exit 1; }
    sleep 10
  done
  say "$1 server up"
}

setsid nohup /root/envs/clm-env/bin/python infra/lm_log_proxy.py $PROXY http://localhost:$PORT $LMLOG \
  > runs/logs/proxy-$PROXY.log 2>&1 < /dev/null &

for m in "${chain[@]}"; do
  serve $m
  queue m5b-$m-smoke $m clm 42
  sed -i '/kv-store-R260-seed42\|log-triage-L320-seed42/!{/^#/!d}' runs/queues/m5b-$m-smoke.txt
  run m5b-$m-smoke 2
  n=$(cat $LMLOG/m5b-$m-clm__{kv-store-R260,log-triage-L320}-seed42.jsonl 2>/dev/null | grep -c '"tool_calls": \[{')
  say "$m smoke: $n calls with parsed tool calls; parser:" \
    "$(grep -o 'FENCE kind=[a-z]*' runs/logs/vllm-m5b-$m.log | sort | uniq -c | tr -s ' \n' ' ')" \
    "fence ids replayed: $(cat $LMLOG/m5b-$m-clm__*-seed42.jsonl | grep -o '"tool_call_id": "fence_' | wc -l)"
  [[ $n -ge 10 ]] || { say "SMOKE_GATE_FAILED $m"; pkill -f "$mine"; exit 1; }
  [[ -n ${SMOKE_ONLY:-} ]] && { say "SMOKE_ONLY: stop after the gate"; pkill -f "$mine"; exit 0; }
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
pkill -f "$mine"
say "ALL DONE"
