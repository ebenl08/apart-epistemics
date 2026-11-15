#!/usr/bin/env bash
# Checklist status of queued ContextBench runs: per-queue done/total, finished rewards, GPU / CPU / RAM / disk.
# Usage: infra/run_status.sh <queue-name>...   e.g. infra/run_status.sh m5n-4b m5n-9b m5n-9b-rl
# Queue <q> = runs/queues/<q>.txt, log runs/logs/queue-<q>.log, trials in the run dir named in the queue file.
cd /workspace/apart-epistemics
echo "== $(date -u +%T) UTC"
for q in "$@"; do
  tot=$(grep -cv '^\s*#\|^\s*$' runs/queues/$q.txt); log=runs/logs/queue-$q.log
  s=$(grep -c " START " $log 2>/dev/null); e=$(grep -c " END " $log 2>/dev/null)
  if grep -q "QUEUE DONE" $log 2>/dev/null; then box="[x]"; else box="[ ]"; fi
  echo "$box $q: finished ${e:-0}/$tot, started ${s:-0}/$tot"
  rd=$(grep -v '^\s*#' runs/queues/$q.txt | awk 'NF{print $4; exit}')
  [[ -d $rd/trials ]] && /root/envs/clm-env/bin/python infra/cb_status.py $rd/trials 2>/dev/null | grep ": done" \
    | awk '{n++; if ($0 ~ /budget_wall/) w++; match($0,/.reward.: [0-9.]+/); s+=substr($0,RSTART+10,RLENGTH-10)}
           END{if(n) printf "      mean reward %.2f over %d done, budget wall %d/%d\n", s/n, n, w, n}'
done
nvidia-smi --query-gpu=index,utilization.gpu,memory.used,memory.total --format=csv,noheader | sed 's/^/  GPU /'
if [[ -f /sys/fs/cgroup/cpu.stat ]]; then  # cgroup v2: usage in us, quota "max period"
  u() { awk '/usage_usec/{print $2*1000}' /sys/fs/cgroup/cpu.stat; }; read qt pd < /sys/fs/cgroup/cpu.max
else                                       # cgroup v1: usage in ns
  u() { cat /sys/fs/cgroup/cpuacct/cpuacct.usage; }
  qt=$(cat /sys/fs/cgroup/cpu/cpu.cfs_quota_us); pd=$(cat /sys/fs/cgroup/cpu/cpu.cfs_period_us)
fi
a=$(u); sleep 2; b=$(u)
echo "  CPU $(awk -v a=$a -v b=$b -v q=$qt -v p=$pd 'BEGIN{c=(b-a)/2e9; if (q>0) printf "%.1f of %.2f cores (%.0f%%)", c, q/p, 100*c*p/q; else printf "%.1f cores", c}')," \
     "RAM $(free -g | awk '/Mem/{print $3"/"$2}') GiB, disk / $(df -h / | awk 'NR==2{print $4}') free"
curl -s localhost:8000/metrics | awk '/^vllm:num_requests_running\{/{r+=$2} /^vllm:num_requests_waiting\{/{w+=$2}
  /^vllm:num_preemptions_total/{n+=$2} /^vllm:kv_cache_usage_perc/{k=$2}
  END{if (NR) printf "  vLLM :8000 running %d, waiting %d, preempt %d, kv %.0f%%\n", r, w, n, 100*k}'
