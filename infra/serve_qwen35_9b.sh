#!/usr/bin/env bash
# Serve Qwen3.5-9B for the CLM reproduction (shared by ContextBench and BCP).
source /root/envs/vllm-env/bin/activate
export HF_HOME=/root/hf_cache   # local disk; /workspace is a quota-limited volume
exec vllm serve Qwen/Qwen3.5-9B --served-model-name qwen35-9b --port ${PORT:-8000} \
  --max-model-len 65536 --language-model-only \
  --enable-auto-tool-choice --tool-call-parser qwen3_coder --reasoning-parser qwen3 \
  --gpu-memory-utilization 0.90 --enable-prefix-caching
