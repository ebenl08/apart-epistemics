"""M5B: vLLM tool-parser plugin. Llama 3.1 / Gemma 3 answer the harness's THOUGHT-then-bash
prompt with a fenced ```bash block instead of a native tool call; the native parsers find
nothing and the harness stalls. This plugin turns the last ```bash block into bash(command=...),
falling back to the family's native parser when there is no block.

Replay contract (keeps the budget, the context mirror and M6 replay faithful):
  content    = the text before the block, verbatim
  tool_call  = bash(command=<block body>), id "fence_<hex>"
  the patched chat templates in infra/chat_templates/ render a "fence_" call back as
  content + "```bash\\n" + command + "\\n```", i.e. the generated text minus any trailing text.
Every reply is logged as one "FENCE kind=..." line in the vLLM log (fallback / native / miss).

Serve: --tool-parser-plugin infra/fence_tool_parser.py --tool-call-parser {llama3_json,pythonic}_fence
Self-check (no vLLM needed): python3 infra/fence_tool_parser.py
"""
from __future__ import annotations

import json
import logging
import re
import uuid
from pathlib import Path

OPEN = re.compile(r"^```(?:bash|sh|shell)[ \t]*\n", re.M)
CLOSE = "\n```"
log = logging.getLogger("vllm.fence_tool_parser")


def split_fence(text: str) -> tuple[str, str | None, dict]:
    """(content, command, info). command is None on a miss; info says why / what was dropped."""
    opens = list(OPEN.finditer(text))
    if not opens:
        return text, None, {"reason": "no_block"}
    o = opens[-1]
    end = text.rfind(CLOSE, o.end() - 1)  # -1: an empty block is "```bash\n```"
    if end < o.end() - 1:
        return text, None, {"reason": "unclosed", "n_blocks": len(opens)}
    cmd = text[o.end():end] if end >= o.end() else ""
    post = text[end + len(CLOSE):]
    info = {"n_blocks": len(opens), "post_chars": len(post.strip())}
    if not cmd.strip():
        return text, None, {**info, "reason": "empty_block"}
    return text[: o.start()], cmd, info


def render(content: str, command: str) -> str:
    """What the templates emit for a fence_ call; must equal the generated text (self-check)."""
    return f"{content}```bash\n{command}\n```"


try:
    from vllm.entrypoints.generate.base.protocol import (ExtractedToolCallInformation,
                                                         FunctionCall, ToolCall)
    from vllm.tool_parsers.abstract_tool_parser import ToolParser, ToolParserManager
    from vllm.tool_parsers.llama_tool_parser import Llama3JsonToolParser
    from vllm.tool_parsers.pythonic_tool_parser import PythonicToolParser
except ImportError:  # self-check on a machine without vLLM
    ToolParser = None

if ToolParser is not None:

    class _FenceParser(ToolParser):
        # Fence first: Llama's native parser json-decodes any "{" in the reply, so a dict inside a
        # THOUGHT or a heredoc could become a bogus call. Native only when there is no block.
        # No structural_tag_model: the native one would constrain decoding toward JSON calls.
        native: type[ToolParser]

        def __init__(self, tokenizer, tools=None):
            super().__init__(tokenizer, tools)
            self._native = self.native(tokenizer, tools)

        def extract_tool_calls(self, model_output, request):
            content, cmd, info = split_fence(model_output)
            if cmd is not None:
                log.info("FENCE kind=fallback %s", json.dumps(info))
                call = ToolCall(id=f"fence_{uuid.uuid4().hex[:24]}",
                                function=FunctionCall(name="bash", arguments=json.dumps(
                                    {"command": cmd}, ensure_ascii=False)))
                return ExtractedToolCallInformation(tools_called=True, tool_calls=[call],
                                                    content=content)
            res = self._native.extract_tool_calls(model_output, request)
            kind = "native" if res.tools_called else "miss"
            log.info("FENCE kind=%s %s", kind, json.dumps({**info, "chars": len(model_output)}))
            return res

        def extract_tool_calls_streaming(self, *a, **k):
            # ponytail: harness and M6 collect.py are non-streaming; stream = native parser only.
            return self._native.extract_tool_calls_streaming(*a, **k)

    class LlamaFence(_FenceParser):
        native = Llama3JsonToolParser

    class PythonicFence(_FenceParser):
        native = PythonicToolParser

    ToolParserManager.register_module(name="llama3_json_fence", module=LlamaFence)
    ToolParserManager.register_module(name="pythonic_fence", module=PythonicFence)


def _selftest() -> None:
    import jinja2

    llama = ("THOUGHT: I need to look at the log first.\n\n```bash\n"
             "grep -c ERROR /app/log.txt && python3 - <<'PY'\nd = {\"name\": 1}\nprint(d)\nPY\n```")
    gemma = ("THOUGHT: Compact turn 3.\n```bash\npython3 - <<'PY'\ns = '```'\nprint(s)\nPY\n```")
    for text in (llama, gemma):
        content, cmd, info = split_fence(text)
        assert cmd is not None and info["post_chars"] == 0, info
        assert render(content, cmd) == text
    assert split_fence("THOUGHT: x\n```bash\nls")[2]["reason"] == "unclosed"
    assert split_fence("THOUGHT: no block")[2]["reason"] == "no_block"
    assert split_fence("```bash\n```")[2]["reason"] == "empty_block"
    c, cmd, info = split_fence("a\n```bash\nls\n```\nthen b\n```sh\npwd\n```\n")
    assert (cmd, info["n_blocks"], c.endswith("then b\n")) == ("pwd", 2, True)

    # Template round trip: the rendered assistant turn must be exactly the generated text.
    tdir = Path(__file__).parent / "chat_templates"
    env = jinja2.Environment(extensions=["jinja2.ext.loopcontrols"])
    env.globals["raise_exception"] = lambda m: (_ for _ in ()).throw(ValueError(m))
    tools = [{"type": "function", "function": {"name": "bash", "parameters": {}}}]
    cases = {
        "tool_chat_template_llama3.1_json.jinja": (llama, "<|start_header_id|>assistant<|end_header_id|>\n\n", "<|eot_id|>"),
        "tool_chat_template_gemma3_pythonic.jinja": (gemma, "<start_of_turn>model\n", "<end_of_turn>"),
    }
    for name, (text, head, eot) in cases.items():
        content, cmd, _ = split_fence(text)
        msgs = [{"role": "system", "content": "sys"}, {"role": "user", "content": "task"},
                {"role": "user", "content": "ledger"},  # harness sends system, user, user
                {"role": "assistant", "content": content, "tool_calls": [
                    {"id": "fence_ab", "type": "function",
                     "function": {"name": "bash", "arguments": {"command": cmd}}}]},
                {"role": "tool", "tool_call_id": "fence_ab", "content": "3"},
                {"role": "user", "content": "[SYSTEM NOTICE] x"}]
        t = env.from_string((tdir / name).read_text())
        out = t.render(messages=msgs, tools=tools, bos_token="<bos>", add_generation_prompt=True,
                       date_string="16 Nov 2026")
        assert head + text + eot in out, (name, out[-400:])
        prompt = t.render(messages=msgs[:3], tools=tools, bos_token="<bos>",
                          add_generation_prompt=True, date_string="16 Nov 2026")
        assert prompt.endswith(head) and "ledger" in prompt, name
        # a native (non-fence) call still renders natively
        msgs[3]["tool_calls"][0]["id"] = "chatcmpl-tool-1"
        native = t.render(messages=msgs, tools=tools, bos_token="<bos>", date_string="16 Nov 2026")
        assert "```bash" not in native.split("ledger", 1)[1].split("3", 1)[0], name
        if "gemma" in name:  # roles merged, so Gemma sees strict user/model alternation
            body = out.split("<start_of_turn>")[1:]
            roles = [b.split("\n", 1)[0] for b in body]
            assert roles == ["user", "model", "user", "model"], roles
    print("fence_tool_parser selftest OK")


if __name__ == "__main__":
    _selftest()
