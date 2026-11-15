#!/usr/bin/env bash
# One-screen M5 status: queues, finished rewards, GPU/CPU/disk, LM-log size, vLLM preemptions.
cd /workspace/apart-epistemics
echo "== $(date -u +%T) UTC"
for q in 4b 9b 9b-rl 9b-rl-b; do
  log=runs/logs/queue-m5-$q.log; [[ -f $log ]] || { echo "[$q] not started"; continue; }
  s=$(grep -c " START " $log); e=$(grep -c " END " $log); d=$(grep -c "QUEUE DONE.*m5-$q.txt" $log)
  echo "[$q] started $s, finished $e$([[ $d == 1 ]] && echo ', QUEUE DONE')"
done
for q in 4b 9b 9b-rl; do
  [[ -d runs/m5-$q/trials ]] && /root/envs/clm-env/bin/python infra/cb_status.py runs/m5-$q/trials 2>/dev/null \
    | grep ": done" | sed -E "s/ reward=\{'reward': ([0-9.]+).*/ r=\1/; s/^/  $q /"
done
nvidia-smi --query-gpu=index,utilization.gpu,memory.used --format=csv,noheader | sed 's/^/  GPU /'
q1=$(awk '/usage_usec/{print $2}' /sys/fs/cgroup/cpu.stat); sleep 2; q2=$(awk '/usage_usec/{print $2}' /sys/fs/cgroup/cpu.stat)
echo "  CPU $(awk -v a=$q1 -v b=$q2 'BEGIN{printf "%.1f of 16.15 cores", (b-a)/2e6}'), RAM $(free -g | awk '/Mem/{print $3}') GiB used"
echo "  disk / $(df -h / | awk 'NR==2{print $4}') free; lmlog $(du -sh runs/m5-lmlog 2>/dev/null | cut -f1), $(ls runs/m5-lmlog 2>/dev/null | wc -l) files"
for p in 8000 8010; do
  curl -s localhost:$p/metrics | awk -v p=$p '/^vllm:num_preemptions_total/{n+=$2} /^vllm:num_requests_running/{r+=$2} /^vllm:num_requests_waiting/{w+=$2} /^vllm:kv_cache_usage_perc/{k=$2} END{printf "  vLLM :%s running %d waiting %d preempt %d kv %.0f%%\n", p, r, w, n, 100*k}'
done
