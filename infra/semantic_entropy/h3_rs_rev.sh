#!/usr/bin/env bash
# Second rejection-sampling worker for one condition (other pod, vLLM already serving that condition's weights):
# walks the 16-trial subset in REVERSE (h3_rs.sh walks forward), takes trials whose plain samples are complete and that
# have no rs result yet, claims each with an atomic mkdir lock, tops up and executes. A trial both workers reach is
# harmless: topup is a no-op once a point has 10 valid calls, and execute skips existing results. Up to 2 at a time.
# Usage: setsid nohup infra/semantic_entropy/h3_rs_rev.sh <cond> > runs/logs/h3-rsrev-<cond>.log 2>&1 < /dev/null &
set -u
c=$1
cd /workspace/apart-epistemics
O=runs/m6-h3/$c; RS=runs/m6-h3/$c-rs; QS=runs/m6-se/queue-h3sub.txt
source /root/m6env.sh
mkdir -p $RS
one() {
  local f=$1 s; s=$(basename $f .jsonl)
  for e in replay.json points.json samples.jsonl; do [[ -e $RS/$s.$e ]] || cp $O/$s.$e $RS/; done
  M6_OUT=$RS $C topup --conc 40 $f 2>&1 | grep -v DEBUG
  echo "$(date -u +%T) topped $s"
  M6_OUT=$RS $C execute $f 2>&1 | grep -v DEBUG
}
left=$(tac $QS)
while [[ -n "$left" ]]; do
  rest=""
  for f in $left; do s=$(basename $f .jsonl)
    [[ -e $RS/$s.topup.done ]] && continue                       # done by either worker
    if [[ -e $O/$s.samples.done ]]; then
      mkdir $RS/$s.claim 2>/dev/null || continue                 # claimed by this worker before
      while (( $(jobs -r | wc -l) >= 2 )); do sleep 10; done
      one $f &
    else rest="$rest $f"; fi
  done
  left=$rest; [[ -n "$left" ]] && sleep 60
done
wait
echo "$(date -u +%T) RSREV DONE"
