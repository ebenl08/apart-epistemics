#!/usr/bin/env bash
# Extra sampler: walks queue-<q> in reverse, stops at the first trial the forward sampler (m6_run.sh) has started.
# Same per-point seeds, so results are unchanged; it only keeps the GPU busy while a few long samples hold up the
# forward sampler's current trial. m6_run.sh's executor picks up trials as their .samples.done appears.
# Usage: M6_OUT=<dir> RCONC=10 setsid nohup infra/semantic_entropy/m6_rev.sh <q> > runs/logs/m6-<q>-rev.log 2>&1 < /dev/null &
source /root/m6env.sh
q=$1; O=${M6_OUT:-runs/m6-se}
for f in $(tac runs/m6-se/queue-$q.txt); do s=$(basename $f .jsonl)
  [[ -e $O/$s.samples.jsonl ]] && { echo "$(date -u +%T) reached started trial $s; stop"; break; }
  $C sample --conc ${RCONC:-10} $f 2>&1 | grep -v DEBUG; echo "$(date -u +%T) rev sampled $s"
done
