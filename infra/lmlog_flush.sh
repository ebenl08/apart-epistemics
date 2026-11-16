#!/usr/bin/env bash
# Move LM-call logs from local disk to the network volume: append each local file to the volume file of the
# same name (local lines are always the later ones), then delete the local copy.
# Usage: infra/lmlog_flush.sh <local_dir> <volume_dir> [name_prefix]
set -u
src=$1; dst=$2; mkdir -p "$dst"
for f in "$src"/${3:-}*.jsonl; do
  [[ -e $f ]] || continue
  cat "$f" >> "$dst/$(basename "$f")" && rm "$f" || echo "lmlog_flush: FAILED $f (kept)"
done
