"""Logging proxy in front of a vLLM OpenAI server: records every LM call (full request + response).

The CLM harness edits its own context, so the saved trajectory loses earlier turns; this log
keeps the exact context the model saw at every call (needed for uncertainty replay later).

Clients use api_base=http://localhost:<port>/<tag>/v1 ; each call is appended as one JSON line
to <log_dir>/<tag>.jsonl: {"t0", "t1", "status", "request", "response"}.
Usage: python lm_log_proxy.py <listen_port> <upstream_base e.g. http://localhost:8000> <log_dir>
"""
import asyncio, json, os, sys, time

from aiohttp import ClientSession, ClientTimeout, web

PORT, UPSTREAM, LOG_DIR = int(sys.argv[1]), sys.argv[2].rstrip("/"), sys.argv[3]
os.makedirs(LOG_DIR, exist_ok=True)
FALLBACK_DIR = "/root/lmlog-fallback"  # container disk, used only when the volume write fails


def append(name: str, line: str) -> None:
    """Runs in a thread: a slow network-volume write (MooseFS stalls of minutes were seen
    on 2026-11-16) then delays only its own trial, not every request through the proxy."""
    try:
        with open(os.path.join(LOG_DIR, name), "a") as f:
            f.write(line)
    except OSError as e:
        os.makedirs(FALLBACK_DIR, exist_ok=True)
        with open(os.path.join(FALLBACK_DIR, name), "a") as f:
            f.write(line)
        print(f"volume write failed ({e}); line saved to {FALLBACK_DIR}/{name}", flush=True)


def drop_empty_assistant(body: bytes) -> tuple[bytes, int]:
    """Ministral (vLLM --tokenizer-mode mistral): mistral-common rejects an assistant turn with empty
    content and no tool call, which the harness sends after an empty reply. Forward without those
    turns; the log keeps the request as sent, plus "dropped_empty_assistant"."""
    try:
        q = json.loads(body)
    except ValueError:
        return body, 0
    if not str(q.get("model", "")).startswith("ministral"):
        return body, 0
    msgs = q.get("messages") or []
    keep = [m for m in msgs if not (m.get("role") == "assistant" and not m.get("tool_calls")
                                    and not (m.get("content") or "").strip())]
    if len(keep) == len(msgs):
        return body, 0
    q["messages"] = keep
    return json.dumps(q).encode(), len(msgs) - len(keep)


async def handle(req: web.Request) -> web.Response:
    tag, rest = req.match_info["tag"], req.match_info["rest"]
    body = await req.read()
    sent, n_drop = drop_empty_assistant(body)
    t0 = time.time()
    async with req.app["s"].request(req.method, f"{UPSTREAM}/v1/{rest}", data=sent,
                                    headers={"Content-Type": "application/json"}) as r:
        out, status = await r.read(), r.status
    if req.method == "POST":
        try:
            rec = {"t0": t0, "t1": time.time(), "status": status,
                   "request": json.loads(body), "response": json.loads(out)}
            if n_drop:
                rec["dropped_empty_assistant"] = n_drop
        except ValueError:
            rec = {"t0": t0, "t1": time.time(), "status": status, "raw": out.decode(errors="replace")}
        # ponytail: one append per call, no lock; fine because each tag is one sequential trial
        # (awaited before replying, so a trial's lines stay in order)
        await asyncio.to_thread(append, f"{os.path.basename(tag)}.jsonl", json.dumps(rec) + "\n")
    return web.Response(body=out, status=status, content_type="application/json")


async def session(app):
    app["s"] = ClientSession(timeout=ClientTimeout(total=None))
    yield
    await app["s"].close()


app = web.Application(client_max_size=256 * 1024 ** 2)
app.cleanup_ctx.append(session)
app.router.add_route("*", "/{tag}/v1/{rest:.*}", handle)
web.run_app(app, port=PORT, access_log=None)
