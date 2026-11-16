#!/usr/bin/env bash
# M6 checklist: per-stage done/total for the trials in runs/m6-se/queue-<q>.txt, GPU / CPU / vLLM, new errors.
# Usage: infra/semantic_entropy/m6_status.sh <q>
cd /workspace/apart-epistemics
q=$1; Q=runs/m6-se/queue-$q.txt; O=${M6_OUT:-runs/m6-se}
n=$(grep -c . $Q); st() { local c=0; for f in $(cat $Q); do s=$(basename $f .jsonl); [[ -e $O/$s$1 ]] && c=$((c+1)); done; echo $c; }
pts=0; smp=0; for f in $(cat $Q); do s=$(basename $f .jsonl)
  [[ -f $O/$s.points.json ]] && pts=$((pts + $(python3 -c "import json;print(len(json.load(open('$O/$s.points.json'))))")))
  [[ -f $O/$s.samples.jsonl ]] && smp=$((smp + $(wc -l < $O/$s.samples.jsonl))); done
r=$(st .replay.json); p=$(st .points.json); sd=$(st .samples.done); x=$(st .jsonl)
b() { [[ $1 -ge $2 ]] && echo "[x]" || echo "[ ]"; }
echo "== $(date -u +%T) UTC  M6 queue $q"
echo "$(b $r $n) replay (Gate A)   $r/$n trials; diverged: $(grep -l '"diverged_at": [0-9]' $O/*.replay.json 2>/dev/null | wc -l)"
echo "$(b $p $n) points            $p/$n trials ($pts points)"
echo "$(b $sd $n) sample (GPU)      $sd/$n trials, $smp/$pts points"
echo "$(b $x $n) execute + SE (CPU) $x/$n trials"
grep -h "gate B" runs/logs/m6-$q-*.log 2>/dev/null | awk '{split($NF,a,"/"); g+=a[1]; t+=a[2]} END{if(t) printf "      Gate B %d/%d\n", g, t}'
nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total --format=csv,noheader | sed 's/^/  GPU /'
{ read qt pd < /sys/fs/cgroup/cpu.max; } 2>/dev/null || { qt=$(cat /sys/fs/cgroup/cpu/cpu.cfs_quota_us); pd=$(cat /sys/fs/cgroup/cpu/cpu.cfs_period_us); }
u() { if [[ -f /sys/fs/cgroup/cpu.stat ]]; then awk '/usage_usec/{print $2*1000}' /sys/fs/cgroup/cpu.stat; else cat /sys/fs/cgroup/cpuacct/cpuacct.usage; fi; }
a=$(u); sleep 2; c=$(u)
echo "  CPU $(awk -v a=$a -v b=$c -v q=$qt -v p=$pd 'BEGIN{x=(b-a)/2e9; if (q>0) printf "%.1f of %.2f cores (%.0f%%)", x, q/p, 100*x*p/q; else printf "%.1f cores", x}'), RAM $(free -g | awk '/Mem/{print $3"/"$2}') GiB, disk / $(df -h / | awk 'NR==2{print $4}') free"
curl -s localhost:8010/metrics | awk '/^vllm:num_requests_running\{/{r+=$2} /^vllm:num_requests_waiting\{/{w+=$2}
  /^vllm:num_preemptions_total/{n+=$2} /^vllm:kv_cache_usage_perc/{k=$2}
  END{if (NR) printf "  vLLM :8010 running %d, waiting %d, preempt %d, kv %.0f%%\n", r, w, n, 100*k; else print "  vLLM :8010 DOWN"}'
e=$(grep -hcE "Traceback|PROMPT MISMATCH|Error" runs/logs/m6-$q-*.log 2>/dev/null | awk '{s+=$1} END{print s+0}')
echo "  errors in logs: $e"; grep -q "M6 DONE" runs/logs/m6-$q-driver.log 2>/dev/null && echo "  M6 DONE"
