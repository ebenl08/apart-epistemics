# Handoff: make M6 `probe.py` work on the M5B models (Gemma 4 E4B, Ministral 3 8B)

From the M5B session, 2026-11-16 (rewritten after the model swap). **Do not apply this while an M6 run is still using
`probe.py` on the volume.** `m6_chain.sh:27-29` runs it from `/workspace/apart-epistemics`, so a mid-run copy changes
the later steps.

## What changed in M5B

Llama 3.1 8B and Gemma 3 were dropped because they couldn't drive the harness's native `bash` tool. M5B now uses two models
with **native tool calls**, like Qwen, so no text parsing and no fence parser are involved.
`infra/fence_tool_parser.py` is unused by these models.

| Served name | Weights | vLLM flags (`infra/serve_m5b.sh`) | Tokenization |
|---|---|---|---|
| `gemma4-e4b` | `google/gemma-4-E4B-it` @ `4ecc2ba6` | `--tool-call-parser gemma4 --reasoning-parser gemma4 --language-model-only --chat-template infra/chat_templates/tool_chat_template_gemma4.jinja` | HF tokenizer + that Jinja template |
| `ministral3-8b` | `mistralai/Ministral-3-8B-Instruct-2512-BF16` @ `f6fae979` | `--tool-call-parser mistral --tokenizer-mode mistral --config-format mistral --load-format mistral --language-model-only` | **mistral-common**, not a Jinja template |

**Thinking:** the harness sends `enable_thinking: true`.
- Gemma 4 thinks, like Qwen did, and its thoughts come back as `reasoning`.
- Ministral 3 Instruct has no thinking mode.

## Changes `infra/semantic_entropy/probe.py` needs

The current behaviour stays the default, so Qwen results are unchanged.

1. **Gemma 4: use vLLM's template.** Both `apply_chat_template` calls (`:73`, `:83`) currently use the tokenizer's built-in template.
   The HF repo's template differs from the vLLM example that was served: the example has an extra empty-thought block
   when thinking is off, among other things. Add an optional `chat_template=` read from an env var such as `M6_CHAT_TEMPLATE`,
   and pass the file above.
2. **Ministral 3: tokenize with what vLLM used.** With `--tokenizer-mode mistral`, vLLM builds prompts with
   `mistral-common`, so HF `apply_chat_template` won't match. The simplest exact route is to ask the server: vLLM's
   `/tokenize` endpoint with `{"model", "messages", "tools", "add_generation_prompt": true}` returns the prompt ids it would use.
   - For `full` (prompt + response), tokenize `messages + [assistant msg]` with `add_generation_prompt: false`.
   - Check that it closes with `</s>`; mistral-common may render a final assistant turn differently from a generated one.
   - The other route is to call `mistral_common`'s `MistralTokenizer.from_file(tekken.json).encode_chat_completion(...)` directly.
3. **End-of-turn trim (`:87-88`).** It is hard-coded to `("", "<|im_end|>")`. Extend it for the new families and print the last 3
   decoded tokens for one point per model to confirm:
   - Gemma 4: `<turn|>`, from the template's turn markers;
   - Ministral: `</s>`.
4. **Layers (`:69`).**
   - Gemma 4 E4B loads as a conditional-generation model, so check `model.model.language_model.layers`.
     It mixes local and global attention layers with different head dims, which doesn't matter for residual-stream hooks.
   - Ministral 3 loads as `Mistral3ForConditionalGeneration` in HF format, also with a `language_model`.
     The served weights were mistral-format `consolidated.safetensors`, while HF needs the `model-*.safetensors` shards from the same repo.
5. **Gemma 4 reasoning.** The response carries `reasoning`, and `probe.py` already copies it to `reasoning_content` (`:80`).
   The vLLM Gemma 4 template renders thinking only for turns after the last user turn (`thinking_gate`), so earlier turns
   drop their thoughts, as in Qwen.

## Checks before trusting probe features on these models

- **The prompt-token mismatch counter must stay at 0** (`len(ids) != usage.prompt_tokens`).
- **`full[len(ids):]` should decode to the logged reasoning, content and tool call plus the end-of-turn token.** Check one
  point per model by eye.

## `collect.py` (SE sampling)

No change expected. It re-posts the logged request to a server started with `infra/serve_m5b.sh`, so the same parsers
and tokenization apply. Gemma 4 samples carry `reasoning`, which `collect.py` already maps.

## Deviation to report

- Ministral 3 has no thinking, while Qwen and Gemma 4 think.
- The model set differs from the plan: Gemma 4 E4B replaces the Gemma 3 4B → 12B chain, and Ministral 3 8B replaces Llama 3.1 8B.
  The reason is format failure with the harness's native-tool-only action space, logged in `.agent/decisions.md`.
