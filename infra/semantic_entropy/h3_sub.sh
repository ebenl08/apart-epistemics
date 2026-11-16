#!/usr/bin/env bash
# H3 on the 16-trial subset (2 trials per family x level, runs/m6-se/queue-h3sub.txt), one condition per call.
#   1. edit weights (ablate.py, deterministic) unless vLLM already serves them; serve under the 9B's name
#   2. plain K = 10 sampling + execution of the subset (forward + reverse sampler), into runs/m6-h3/<cond>/
#   3. if TOPUP=1: rejection sampling into runs/m6-h3/<cond>-rs/ (top up to 10 valid tool calls, cap 40), re-execute
# Usage: [WAITFOR=<log>] [TOPUP=1] setsid nohup infra/semantic_entropy/h3_sub.sh <cond> <lam> <spec> > runs/logs/h3-sub-<cond>.log 2>&1 < /dev/null &
#   spec = runs/m6-probe/direction-m5-9b.npz | random:<seed>
set -u
c=$1; lam=$2; spec=$3
cd /workspace/apart-epistemics
export HF_HOME=/root/hf_cache
PY=/root/envs/vllm-env/bin/python
[[ -n ${WAITFOR:-} ]] && until grep -q "H3 DONE" $WAITFOR; do sleep 30; done
W=/root/models/h3-$c; O=runs/m6-h3/$c; QS=runs/m6-se/queue-h3sub.txt
echo "$(date -u +%T) SUB START $c (lam $lam, $spec)"

if curl -sf localhost:8010/v1/models > /dev/null && [[ -d $W ]]; then
  echo "$(date -u +%T) reusing running vLLM ($W)"
else
  SRC=$(/root/envs/hf/bin/python -c "from huggingface_hub import snapshot_download as s; print(s('Qwen/Qwen3.5-9B'))" 2>/dev/null | tail -1)
  $PY infra/semantic_entropy/ablate.py make $SRC $spec $lam $W || { echo "ABLATE FAILED"; exit 1; }
  echo "edited: $($PY infra/semantic_entropy/ablate.py check $W $W/direction.npy 2>/dev/null | tail -1)"
  ok=0
  for try in 1 2; do
    ( source /root/envs/vllm-env/bin/activate
      setsid nohup vllm serve $W --served-model-name qwen35-9b --port 8010 --max-model-len 65536 --language-model-only \
        --enable-auto-tool-choice --tool-call-parser qwen3_coder --reasoning-parser qwen3 \
        --gpu-memory-utilization 0.90 --enable-prefix-caching > runs/logs/vllm-h3-$c.$try.log 2>&1 < /dev/null & )
    for i in $(seq 1 90); do curl -sf localhost:8010/v1/models > /dev/null && { ok=1; break; }
      pgrep -f "vllm serve $W" > /dev/null || break; sleep 10; done
    [[ $ok == 1 ]] && break; pkill -f "vllm serve $W"; sleep 10
  done
  [[ $ok == 1 ]] || { echo "VLLM FAILED"; exit 1; }
  echo "$(date -u +%T) vLLM up"
fi

# 2. plain K = 10 on the subset
mkdir -p $O; for f in $(cat $QS); do s=$(basename $f .jsonl); for e in replay.json points.json; do
  [[ -e $O/$s.$e ]] || cp runs/m6-se/$s.$e $O/; done; done
cp $QS runs/m6-se/queue-h3${c}sub.txt
M6_OUT=$O RCONC=10 setsid nohup infra/semantic_entropy/m6_rev.sh h3${c}sub > runs/logs/m6-h3${c}sub-rev.log 2>&1 < /dev/null &
M6_OUT=$O CONC=20 infra/semantic_entropy/m6_run.sh h3${c}sub > runs/logs/m6-h3${c}sub-driver.log 2>&1
grep -q "M6 DONE" runs/logs/m6-h3${c}sub-driver.log || { echo "DRIVER FAILED"; exit 1; }
echo "$(date -u +%T) plain K=10 done"

# 3. rejection sampling
if [[ ${TOPUP:-0} == 1 ]]; then
  R=runs/m6-h3/$c-rs; mkdir -p $R
  for f in $(cat $QS); do s=$(basename $f .jsonl)
    for e in replay.json points.json samples.jsonl samples.done; do [[ -e $R/$s.$e ]] || cp $O/$s.$e $R/; done; done
  source /root/m6env.sh
  M6_OUT=$R xargs -P 3 -I{} sh -c "$C topup --conc 10 {} 2>&1 | grep -v DEBUG; echo topped {}" < $QS
  echo "$(date -u +%T) topup done"
  M6_OUT=$R xargs -P 6 -I{} sh -c "$C execute {} 2>&1 | grep -v DEBUG" < $QS
  echo "$(date -u +%T) rs execute done ($(ls $R | grep jsonl | grep -v samples | wc -l)/16)"
fi

pkill -f "vllm serve $W"; sleep 20; rm -rf $W
echo "$(date -u +%T) H3 DONE"
