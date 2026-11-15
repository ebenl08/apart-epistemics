#!/usr/bin/env bash
# M6 pipeline for one queue: replay all -> points -> sample (GPU, one trial at a time) || execute (CPU, as samples finish).
# Usage: setsid nohup infra/semantic_entropy/m6_run.sh <q> [exec_parallel] > runs/logs/m6-<q>-driver.log 2>&1 < /dev/null &
source /root/m6env.sh
q=$1; P=${2:-6}; Q=runs/m6-se/queue-$q.txt; O=runs/m6-se; LG=runs/logs/m6-$q
echo "$(date -u +%T) START $q ($(wc -l < $Q) trials)"
xargs -P $P -I{} sh -c "$C replay {} 2>&1 | grep -v DEBUG" < $Q >> $LG-replay.log
$C points $(cat $Q) >> $LG-replay.log 2>&1
echo "$(date -u +%T) replay+points done"
( for f in $(cat $Q); do $C sample --conc ${CONC:-8} $f 2>&1 | grep -v DEBUG; echo "$(date -u +%T) sampled $(basename $f)"; done ) >> $LG-sample.log &
SP=$!
# executor: run each trial once its samples are complete
left=$(cat $Q)
while [[ -n "$left" ]]; do
  ready=""; rest=""
  for f in $left; do s=$(basename $f .jsonl); [[ -f $O/$s.samples.done ]] && ready="$ready $f" || rest="$rest $f"; done
  if [[ -n "$ready" ]]; then echo $ready | tr ' ' '\n' | grep . | xargs -P $P -I{} sh -c "$C execute {} 2>&1 | grep -v DEBUG" >> $LG-execute.log; fi
  left=$rest
  if [[ -n "$left" ]] && ! kill -0 $SP 2>/dev/null; then
    # sampler finished; anything still not done failed to sample
    miss=""; for f in $left; do s=$(basename $f .jsonl); [[ -f $O/$s.samples.done ]] || miss="$miss $s"; done
    [[ -n "$miss" ]] && { echo "$(date -u +%T) SAMPLE INCOMPLETE:$miss"; left=$(for f in $left; do s=$(basename $f .jsonl); [[ -f $O/$s.samples.done ]] && echo $f; done); }
  fi
  [[ -n "$left" ]] && sleep 30
done
wait $SP
echo "$(date -u +%T) M6 DONE $q"
