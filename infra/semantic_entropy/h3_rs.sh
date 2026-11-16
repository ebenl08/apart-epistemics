#!/usr/bin/env bash
# H3 rejection sampling for one condition on the 16-trial subset, into runs/m6-h3/<cond>-rs/.
# Serves the condition's edited weights (ablate.py is deterministic), then for each subset trial whose plain samples are
# complete (runs/m6-h3/<cond>/<trial>.samples.done, possibly written by another pod): copy, top up to 10 valid tool
# calls per point (cap 40, new seeds), execute. Up to 3 trials at a time.
# Usage: setsid nohup infra/semantic_entropy/h3_rs.sh <cond> <lam> <spec> > runs/logs/h3-rs-<cond>.log 2>&1 < /dev/null &
set -u
c=$1; lam=$2; spec=$3
cd /workspace/apart-epistemics
export HF_HOME=/root/hf_cache
PY=/root/envs/vllm-env/bin/python
W=/root/models/h3-$c; O=runs/m6-h3/$c; RS=runs/m6-h3/$c-rs; QS=runs/m6-se/queue-h3sub.txt
echo "$(date -u +%T) RS START $c"
if ! curl -sf localhost:8010/v1/models > /dev/null; then
  SRC=$(/root/envs/hf/bin/python -c "from huggingface_hub import snapshot_download as s; print(s('Qwen/Qwen3.5-9B'))" 2>/dev/null | tail -1)
  [[ -d $W ]] || $PY infra/semantic_entropy/ablate.py make $SRC $spec $lam $W || { echo "ABLATE FAILED"; exit 1; }
  ok=0
  for try in 1 2; do
    ( source /root/envs/vllm-env/bin/activate
      setsid nohup vllm serve $W --served-model-name qwen35-9b --port 8010 --max-model-len 65536 --language-model-only \
        --enable-auto-tool-choice --tool-call-parser qwen3_coder --reasoning-parser qwen3 \
        --gpu-memory-utilization 0.90 --enable-prefix-caching > runs/logs/vllm-h3rs-$c.$try.log 2>&1 < /dev/null & )
    for i in $(seq 1 90); do curl -sf localhost:8010/v1/models > /dev/null && { ok=1; break; }
      pgrep -f "vllm serve $W" > /dev/null || break; sleep 10; done
    [[ $ok == 1 ]] && break; pkill -f "vllm serve $W"; sleep 10
  done
  [[ $ok == 1 ]] || { echo "VLLM FAILED"; exit 1; }
fi
echo "$(date -u +%T) vLLM up"
source /root/m6env.sh   # note: sets R (repo root) and C
mkdir -p $RS
one() {  # $1 = log path
  local f=$1 s; s=$(basename $f .jsonl)
  for e in replay.json points.json samples.jsonl; do [[ -e $RS/$s.$e ]] || cp $O/$s.$e $RS/; done
  M6_OUT=$RS $C topup --conc 40 $f 2>&1 | grep -v DEBUG
  echo "$(date -u +%T) topped $s"
  M6_OUT=$RS $C execute $f 2>&1 | grep -v DEBUG
}
left=$(cat $QS)
while [[ -n "$left" ]]; do
  rest=""
  for f in $left; do s=$(basename $f .jsonl)
    if [[ -e $O/$s.samples.done ]]; then
      while (( $(jobs -r | wc -l) >= 3 )); do sleep 10; done
      one $f &
    else rest="$rest $f"; fi
  done
  left=$rest; [[ -n "$left" ]] && sleep 60
done
wait
echo "$(date -u +%T) rs executed $(ls $RS | grep jsonl | grep -v samples | wc -l)/16"
pkill -f "vllm serve $W"; sleep 20; rm -rf $W
echo "$(date -u +%T) RS DONE"
