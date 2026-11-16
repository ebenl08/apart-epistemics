#!/usr/bin/env bash
# Pod 2 helps the slower H3 condition once its own condition is done: rebuild the same edited weights
# (ablate.py is deterministic), serve them, and sample that condition's trials from the middle of the queue forward,
# stopping at the first trial another sampler has started. Same per-point seeds, so results are unchanged.
# Pod 1's m6_run.sh executor (shared volume) executes trials as their .samples.done appears.
# Usage: setsid nohup infra/semantic_entropy/h3_help.sh <own cond> <cond to help> > runs/logs/h3-help.log 2>&1 < /dev/null &
set -u
own=$1; c=$2
cd /workspace/apart-epistemics
export HF_HOME=/root/hf_cache
until grep -q "H3 DONE" runs/logs/h3-chain-$own.log; do sleep 30; done
echo "$(date -u +%T) $own done; helping $c"
SRC=$(/root/envs/hf/bin/python -c "from huggingface_hub import snapshot_download as s; print(s('Qwen/Qwen3.5-9B'))" 2>/dev/null | tail -1)
[[ $c == dom ]] && spec=runs/m6-probe/direction-m5-9b.npz || spec=random:0
W=/root/models/h3-$c
/root/envs/vllm-env/bin/python infra/semantic_entropy/ablate.py make $SRC $spec 0 $W || { echo "ABLATE FAILED"; exit 1; }
( source /root/envs/vllm-env/bin/activate
  setsid nohup vllm serve $W --served-model-name qwen35-9b --port 8010 --max-model-len 65536 --language-model-only \
    --enable-auto-tool-choice --tool-call-parser qwen3_coder --reasoning-parser qwen3 \
    --gpu-memory-utilization 0.90 --enable-prefix-caching > runs/logs/vllm-h3-help-$c.log 2>&1 < /dev/null & )
for i in $(seq 1 90); do curl -sf localhost:8010/v1/models > /dev/null && break; sleep 10; done
curl -sf localhost:8010/v1/models > /dev/null || { echo "VLLM FAILED"; exit 1; }
echo "$(date -u +%T) vLLM up ($c weights)"
source /root/m6env.sh; export M6_OUT=runs/m6-h3/$c
Q=runs/m6-se/queue-h3$c.txt; n=$(wc -l < $Q)
for f in $(tail -n +$((n / 2)) $Q); do s=$(basename $f .jsonl)
  [[ -e $M6_OUT/$s.samples.jsonl ]] && { echo "$(date -u +%T) reached started trial $s; stop"; break; }
  $C sample --conc ${HCONC:-20} $f 2>&1 | grep -v DEBUG; echo "$(date -u +%T) help sampled $s"
done
pkill -f "vllm serve $W"; rm -rf $W
echo "$(date -u +%T) HELP DONE"
