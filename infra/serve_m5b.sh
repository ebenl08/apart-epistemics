#!/usr/bin/env bash
# M5B: download (pinned revision) and serve a non-Qwen model.
# gemma4-e4b / ministral3-8b: native tool calls (vLLM's own parsers), the M5B models since 2026-11-16.
# llama31-8b / gemma3-*: the dropped first attempt, via the fenced-bash fallback parser (infra/fence_tool_parser.py).
# Usage: CUDA_VISIBLE_DEVICES=<gpu> PORT=<port> infra/serve_m5b.sh <gemma4-e4b|ministral3-8b|llama31-8b|gemma3-4b|gemma3-12b>
# Needs /root/.hf_token (gated models). Only gemma4-e4b has a thinking mode (reasoning parser gemma4).
set -euo pipefail
ROOT=/workspace/apart-epistemics
case $1 in
  llama31-8b) repo=meta-llama/Llama-3.1-8B-Instruct; rev=0e9e39f249a16976918f6564b8830bc894c89659
              extra=(--tool-call-parser llama3_json_fence --chat-template-content-format string --tool-parser-plugin $ROOT/infra/fence_tool_parser.py --chat-template $ROOT/infra/chat_templates/tool_chat_template_llama3.1_json.jinja) ;;
  gemma3-4b)  repo=google/gemma-3-4b-it; rev=093f9f388b31de276ce2de164bdc2081324b9767
              extra=(--tool-call-parser pythonic_fence --chat-template-content-format string --tool-parser-plugin $ROOT/infra/fence_tool_parser.py --language-model-only --chat-template $ROOT/infra/chat_templates/tool_chat_template_gemma3_pythonic.jinja) ;;
  gemma3-12b) repo=google/gemma-3-12b-it; rev=96b6f1eccf38110c56df3a15bffe176da04bfd80
              extra=(--tool-call-parser pythonic_fence --chat-template-content-format string --tool-parser-plugin $ROOT/infra/fence_tool_parser.py --language-model-only --chat-template $ROOT/infra/chat_templates/tool_chat_template_gemma3_pythonic.jinja) ;;
  gemma4-e4b) repo=google/gemma-4-E4B-it; rev=4ecc2ba63bcac23ba4a767fc87025b1450f84c9c  # thinking on (harness sends enable_thinking)
              extra=(--tool-call-parser gemma4 --reasoning-parser gemma4 --language-model-only --chat-template $ROOT/infra/chat_templates/tool_chat_template_gemma4.jinja) ;;
  ministral3-8b) repo=mistralai/Ministral-3-8B-Instruct-2512-BF16; rev=f6fae9795746f63c9be8344932f01275f3c63734  # BF16: A40 has no FP8
              extra=(--tool-call-parser mistral --tokenizer-mode mistral --config-format mistral --load-format mistral --language-model-only) ;;
  *) echo "unknown model $1"; exit 2 ;;
esac
dir=/root/models/$1
if [[ ! -f $dir/.done ]]; then
  HF_TOKEN=$(cat /root/.hf_token) HF_HUB_ENABLE_HF_TRANSFER=1 /root/envs/hf/bin/hf download $repo --revision $rev \
    --local-dir $dir --exclude "original/*"
  echo $rev > $dir/.done
fi
source /root/envs/vllm-env/bin/activate  # torch compile needs the venv's ninja on PATH
exec vllm serve $dir --served-model-name $1 --port ${PORT:-8000} --max-model-len 65536 \
  --enable-auto-tool-choice "${extra[@]}" --gpu-memory-utilization 0.90 --enable-prefix-caching
