#!/usr/bin/env bash
# Rebuild the CLM reproduction env on a fresh RunPod pod (container disk is not persistent).
# Repo, data/ and runs/ live on the network volume at /workspace; venvs, weights, rootfs on /.
# Usage: nohup infra/setup_pod.sh > runs/logs/setup-pod.log 2>&1 &
set -euxo pipefail
ROOT=/workspace/apart-epistemics
export UV_CACHE_DIR=/root/uv_cache UV_LINK_MODE=copy HF_HOME=/root/hf_cache

apt-get update -qq && apt-get install -y -qq proot

# Weights first (background): 4B + 9B on the container disk, not the volume (user: no need to persist).
uv venv -q /root/envs/hf --python 3.12 && VIRTUAL_ENV=/root/envs/hf uv pip install -q "huggingface_hub[hf_transfer]"
# SKIP_QWEN=1 for runs that serve other models (M5B downloads its own in infra/serve_m5b.sh).
[[ -n "${SKIP_QWEN:-}" ]] || ( export HF_HUB_ENABLE_HF_TRANSFER=1
  /root/envs/hf/bin/hf download Qwen/Qwen3.5-4B && /root/envs/hf/bin/hf download Qwen/Qwen3.5-9B
  echo WEIGHTS_DONE ) > /root/hf_download.log 2>&1 &

uv venv -q /root/envs/vllm-env --python 3.12
VIRTUAL_ENV=/root/envs/vllm-env uv pip install -q vllm==0.33.0
# vLLM 0.33.0's Mistral tool grammar calls get_lark_from_jinja without force_tool_names (added in mistral-common 1.13)
VIRTUAL_ENV=/root/envs/vllm-env uv pip install -q "mistral-common==1.12.0"
uv venv -q /root/envs/clm-env --python 3.12
VIRTUAL_ENV=/root/envs/clm-env uv pip install -q -e "$ROOT/context-language-models" \
  -e "$ROOT/data/ContextBench[tokenizer]" matplotlib pandas pyarrow

# Pin to the M5 rootfs (from its setup log on the volume) so logged trials stay replayable.
/root/envs/clm-env/bin/python "$ROOT/infra/pull_rootfs.py" /root/rootfs/py312slim \
  $(grep -oE 'rootfs ok sha256:[0-9a-f]+' "$ROOT/runs/logs/setup-pod.log" | head -1 | cut -d' ' -f3)
wait
echo SETUP_DONE
