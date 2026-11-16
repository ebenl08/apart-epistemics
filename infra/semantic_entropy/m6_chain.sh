#!/usr/bin/env bash
# Full M6 for one model, unattended: serve -> Pass 1-3 (m6_run.sh) -> Part 2 analysis -> Part 3 probes.
# Usage: setsid nohup infra/semantic_entropy/m6_chain.sh <q> <run prefix> <weights> <served name> > runs/logs/m6-<q>-chain.log 2>&1 < /dev/null &
# e.g.   m6_chain.sh 9brl m5-9b-rl /root/models/clm-9b-rl/converted qwen35-9b-rl
# Trials: the same 42 cells/seeds as the 9B queue (runs/m6-se/queue-9b.txt), with the prefix swapped.
set -u
q=$1; pre=$2; W=$3; NAME=$4
cd /workspace/apart-epistemics
sed "s|/m5-9b__|/${pre}__|" runs/m6-se/queue-9b.txt > runs/m6-se/queue-$q.txt
for f in $(cat runs/m6-se/queue-$q.txt); do [[ -f $f ]] || { echo "MISSING LOG $f"; exit 1; }; done
echo "$(date -u +%T) CHAIN START $q: $(wc -l < runs/m6-se/queue-$q.txt) trials, model $W as $NAME"

source /root/envs/vllm-env/bin/activate
setsid nohup vllm serve $W --served-model-name $NAME --port 8010 --max-model-len 65536 --language-model-only \
  --enable-auto-tool-choice --tool-call-parser qwen3_coder --reasoning-parser qwen3 \
  --gpu-memory-utilization 0.90 --enable-prefix-caching > runs/logs/vllm-m6-$q.log 2>&1 < /dev/null &
until curl -sf localhost:8010/v1/models > /dev/null; do sleep 10; done
echo "$(date -u +%T) vLLM up"; deactivate

CONC=${CONC:-20} infra/semantic_entropy/m6_run.sh $q > runs/logs/m6-$q-driver.log 2>&1
grep -q "M6 DONE" runs/logs/m6-$q-driver.log || { echo "DRIVER FAILED"; exit 1; }
pkill -f "vllm serve $W"; sleep 20
echo "$(date -u +%T) Pass 1-3 done; vLLM stopped"

source /root/m6env.sh
python3 infra/semantic_entropy/analyze.py $pre runs/m6-se/analysis > runs/logs/m6-$q-analyze.log 2>&1 && echo "$(date -u +%T) Part 2 done"
python3 infra/semantic_entropy/probe.py dump $pre > runs/logs/m6-$q-probe-dump.log 2>&1
M6_MODEL=$W /root/envs/vllm-env/bin/python infra/semantic_entropy/probe.py extract $pre > runs/logs/m6-$q-probe-extract.log 2>&1
/root/envs/vllm-env/bin/python infra/semantic_entropy/probe.py fit $pre > runs/logs/m6-$q-probe-fit.log 2>&1
[[ -f runs/m6-probe/probe-$pre.md ]] && echo "$(date -u +%T) Part 3 done" || echo "PROBE FAILED"
echo "$(date -u +%T) CHAIN DONE $q"
