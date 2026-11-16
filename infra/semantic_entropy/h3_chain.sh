#!/usr/bin/env bash
# H3 decision level, unattended. Per condition: edit the 9B weights (ablate.py), check the residual projection,
# serve the edited model under the 9B's name, resample + execute the same 1409 9B decision points, then compare SE.
# Usage: setsid nohup infra/semantic_entropy/h3_chain.sh [conds, default "dom rand"] > runs/logs/h3-chain-<x>.log 2>&1 < /dev/null &
# Conditions can run on separate pods (shared volume); the analysis covers every condition that is complete.
set -u
cd /workspace/apart-epistemics
export HF_HOME=/root/hf_cache
PY=/root/envs/vllm-env/bin/python
# wait only for the 9B-RL GPU stages (probe extraction); its CPU-only probe fit may still be running
until grep -q "Part 2 done" runs/logs/m6-9brl-chain.log && [[ -f runs/logs/m6-9brl-probe-fit.log ]]; do sleep 30; done
rm -rf /root/models/clm-9b-rl   # disk: 9B-RL weights no longer needed (fit uses saved activations)
SRC=$(HF_HUB_ENABLE_HF_TRANSFER=1 /root/envs/hf/bin/python -c "from huggingface_hub import snapshot_download as s; print(s('Qwen/Qwen3.5-9B'))" 2>/dev/null | tail -1)
[[ -f $SRC/config.json && $(du -sLm $SRC | cut -f1) -gt 15000 ]] || { echo "BASE WEIGHTS MISSING ($SRC)"; exit 1; }
echo "$(date -u +%T) H3 START; base weights $SRC"

serve() {  # $1 = weights dir; retried once: the first vLLM start on a pod died silently during flashinfer JIT (9B-RL run)
  for try in 1 2; do
    ( source /root/envs/vllm-env/bin/activate
      setsid nohup vllm serve $1 --served-model-name qwen35-9b --port 8010 --max-model-len 65536 --language-model-only \
        --enable-auto-tool-choice --tool-call-parser qwen3_coder --reasoning-parser qwen3 \
        --gpu-memory-utilization 0.90 --enable-prefix-caching > runs/logs/vllm-h3-$c.$try.log 2>&1 < /dev/null & )
    for i in $(seq 1 90); do curl -sf localhost:8010/v1/models > /dev/null && return 0
      pgrep -f "vllm serve $1" > /dev/null || break; sleep 10; done
    pkill -f "vllm serve $1"; sleep 10; echo "$(date -u +%T) vLLM start $try failed"
  done
  return 1
}

CONDS=${*:-dom rand}
for c in $CONDS; do
  [[ $c == dom ]] && spec=runs/m6-probe/direction-m5-9b.npz || spec=random:0
  W=/root/models/h3-$c; O=runs/m6-h3/$c
  $PY infra/semantic_entropy/ablate.py make $SRC $spec 0 $W || { echo "ABLATE FAILED $c"; exit 1; }
  echo "$(date -u +%T) $c: edited weights in $W"
  echo "base:   $($PY infra/semantic_entropy/ablate.py check $SRC $W/direction.npy 2>/dev/null | tail -1)"
  echo "edited: $($PY infra/semantic_entropy/ablate.py check $W $W/direction.npy 2>/dev/null | tail -1)"
  mkdir -p $O; cp runs/m6-se/m5-9b__*.replay.json runs/m6-se/m5-9b__*.points.json $O/
  cp runs/m6-se/queue-9b.txt runs/m6-se/queue-h3$c.txt
  serve $W || { echo "VLLM FAILED $c"; exit 1; }
  echo "$(date -u +%T) $c: vLLM up"
  M6_OUT=$O CONC=20 infra/semantic_entropy/m6_run.sh h3$c > runs/logs/m6-h3$c-driver.log 2>&1
  grep -q "M6 DONE" runs/logs/m6-h3$c-driver.log || { echo "DRIVER FAILED $c"; exit 1; }
  pkill -f "vllm serve $W"; sleep 20; rm -rf $W
  echo "$(date -u +%T) $c: done"
done

source /root/m6env.sh
done_c=$(for c in dom rand; do [[ $(ls runs/m6-h3/$c 2>/dev/null | grep jsonl | grep -v -e samples -e replay -e points | wc -l) -ge 42 ]] && echo $c; done)
python3 infra/semantic_entropy/h3_analyze.py runs/m6-h3/h3-decision.md $done_c > runs/logs/h3-analyze.log 2>&1 \
  && echo "$(date -u +%T) analysis done" || echo "ANALYSIS FAILED"
echo "$(date -u +%T) H3 DONE"
