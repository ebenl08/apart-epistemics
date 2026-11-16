# Handoff: make M6 `probe.py` work on Llama 3.1 / Gemma 3 (M5B models)

From the M5B session, 2026-11-16. **Do not apply this while an M6 run is still using `probe.py` on the volume.**
`m6_chain.sh:27-29` runs it from `/workspace/apart-epistemics`, so a mid-run copy changes the later steps.

## Why

M5B serves Llama 3.1 8B and Gemma 3 through a fenced-bash fallback parser,
`infra/fence_tool_parser.py`. The models answer with `THOUGHT … ```bash <cmd>```` instead of a native tool call. The
parser turns this into `content` = the text before the block, plus a `bash` tool call with id `fence_<hex>`.
The patched templates in `infra/chat_templates/` replay a `fence_` call as `content + "```bash\n" + cmd + "\n```"`.
That is the text the model generated.

When M6 runs on these models, the probe has to re-tokenize the conversation with those **same templates**. Otherwise
the TBG and SLT positions land on text the model never saw or wrote.

## Changes to `infra/semantic_entropy/probe.py`

The current behaviour stays the default: with no new env vars, Qwen results are unchanged.

1. **Template.** `extract` calls `tok.apply_chat_template(...)` twice (`:73` prompt, `:83` prompt + response). Both
   use the tokenizer's built-in template. Add an optional template:
   ```python
   TPL = os.environ.get("M6_CHAT_TEMPLATE")          # e.g. infra/chat_templates/tool_chat_template_llama3.1_json.jinja
   TPL = Path(TPL).read_text() if TPL else None
   ... tok.apply_chat_template(..., chat_template=TPL, **kw)   # both calls
   ```
   These are the templates vLLM serves with (`--chat-template` in `infra/serve_m5b.sh`):
   - `llama31-8b`: `tool_chat_template_llama3.1_json.jinja`
   - `gemma3-4b` / `gemma3-12b`: `tool_chat_template_gemma3_pythonic.jinja`

2. **End-of-turn trim (`:87-88`).** It is hard-coded for Qwen: `("", "<|im_end|>")`. Make it per family:
   - Llama 3.1 closes a turn with `<|eot_id|>`.
   - Gemma 3 closes with `<end_of_turn>` + `\n`.

   Simplest is to strip any of them, since the set is harmless for Qwen:
   ```python
   EOT = ("", "<|im_end|>", "<|eot_id|>", "<end_of_turn>")
   while i_slt > i_tbg and tok.decode([full[i_slt]]).strip() in EOT:
   ```

3. **`model.model.layers` (`:69`).** Llama has `model.model.layers`. Gemma 3 loaded as `Gemma3ForConditionalGeneration` has
   `model.model.language_model.layers`, which the existing fallback covers. If Gemma is loaded as
   `Gemma3ForCausalLM`, check the attribute path. vLLM serves it with `--language-model-only`, so the weights are the same.

4. **The `<|im_end|>` comment at `:87`.** Update it to name all three families.

`norm_msgs` (`:110`) already turns tool-call argument strings into dicts, which the `fence_` branch of the template
needs (`tool_call.arguments.command`). It keeps `id`, so no change is needed there.

## Checks before trusting probe features on these models

- **The prompt-token mismatch counter must stay at 0.** `extract` prints "prompt-token mismatches so far"
  (`len(ids) != usage.prompt_tokens`). A nonzero count means the template isn't the one vLLM used.
- **A stronger check, once per model:** the slice `full[len(ids):]` should decode to the logged response text plus the end-of-turn
  token. A mismatch means a `fence_` reply had text after the block; the parser drops it and logs `post_chars` in
  the vLLM log as `FENCE kind=fallback {... "post_chars": N}`. For those points SLT sits on the block's closing
  fence, not on the very last generated token. Count them and decide whether to drop them.
- The Llama template's date is now fixed at `26 Jul 2024` (no `strftime_now`), so replays on a later day match.

## `collect.py` (SE sampling and execution): no change expected

- It re-posts the logged request with `n=K` to vLLM. The server runs the same parser on every sample, so each sample
  ends up as either a `fence_` call or `no_tool_call`.
- **The vLLM server for SE must be started with `infra/serve_m5b.sh`, not the stock tool parser.** Only that server has
  the plugin and templates. With a stock server, every sample comes back as `no_tool_call` and the logged prompts won't match
  (`PROMPT MISMATCH`).
- SE `n_no_command` on these models also counts format misses, such as an unclosed or empty block. Report it with
  the FENCE `miss` rate so a format failure isn't read as uncertainty.

## Deviation to report

Llama and Gemma act through text-parsed ```bash blocks, while Qwen used native tool calls. The prompt and sampling are
unchanged. The decision and its rationale are in `.agent/decisions.md` (2026-11-16 M5B fence parser).
