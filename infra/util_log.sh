#!/usr/bin/env bash
# Log GPU and CPU utilization as CSV every N seconds (default 30).
# Usage: nohup infra/util_log.sh <out.csv> [interval] &
# Columns: utc, gpu_util%, gpu_mem_used_MiB, gpu_mem_total_MiB, gpu_power_W,
#          cpu_busy% (all cores, over the interval), load1, mem_used_GiB
set -u
OUT=$1; INT=${2:-30}
[[ -s "$OUT" ]] || echo "utc,gpu_util,gpu_mem_used_mib,gpu_mem_total_mib,gpu_power_w,cpu_busy,load1,mem_used_gib" > "$OUT"
read -r _ a b c d e f g _ < /proc/stat; prev_idle=$((d+e)); prev_tot=$((a+b+c+d+e+f+g))
while sleep "$INT"; do
  read -r _ a b c d e f g _ < /proc/stat; idle=$((d+e)); tot=$((a+b+c+d+e+f+g))
  cpu=$(awk -v di=$((idle-prev_idle)) -v dt=$((tot-prev_tot)) 'BEGIN{printf "%.1f", dt?100*(1-di/dt):0}')
  prev_idle=$idle; prev_tot=$tot
  gpu=$(nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total,power.draw --format=csv,noheader,nounits | head -1 | tr -d ' ')
  load=$(cut -d' ' -f1 /proc/loadavg)
  mem=$(free -g | awk '/Mem:/{print $3}')
  echo "$(date -u +%FT%TZ),$gpu,$cpu,$load,$mem" >> "$OUT"
done
