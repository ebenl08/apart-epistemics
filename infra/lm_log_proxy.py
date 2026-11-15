"""Logging proxy in front of a vLLM OpenAI server: records every LM call (full request + response).

The CLM harness edits its own context, so the saved trajectory loses earlier turns; this log
keeps the exact context the model saw at every call (needed for uncertainty replay later).

Clients use api_base=http://localhost:<port>/<tag>/v1 ; each call is appended as one JSON line
to <log_dir>/<tag>.jsonl: {"t0", "t1", "status", "request", "response"}.
Usage: python lm_log_proxy.py <listen_port> <upstream_base e.g. http://localhost:8000> <log_dir>
"""
import json, os, sys, time

from aiohttp import ClientSession, ClientTimeout, web

PORT, UPSTREAM, LOG_DIR = int(sys.argv[1]), sys.argv[2].rstrip("/"), sys.argv[3]
os.makedirs(LOG_DIR, exist_ok=True)


async def handle(req: web.Request) -> web.Response:
    tag, rest = req.match_info["tag"], req.match_info["rest"]
    body = await req.read()
    t0 = time.time()
    async with req.app["s"].request(req.method, f"{UPSTREAM}/v1/{rest}", data=body,
                                    headers={"Content-Type": "application/json"}) as r:
        out, status = await r.read(), r.status
    if req.method == "POST":
        try:
            rec = {"t0": t0, "t1": time.time(), "status": status,
                   "request": json.loads(body), "response": json.loads(out)}
        except ValueError:
            rec = {"t0": t0, "t1": time.time(), "status": status, "raw": out.decode(errors="replace")}
        # ponytail: one append per call, no lock; fine because each tag is one sequential trial
        with open(os.path.join(LOG_DIR, f"{os.path.basename(tag)}.jsonl"), "a") as f:
            f.write(json.dumps(rec) + "\n")
    return web.Response(body=out, status=status, content_type="application/json")


async def session(app):
    app["s"] = ClientSession(timeout=ClientTimeout(total=None))
    yield
    await app["s"].close()


app = web.Application(client_max_size=256 * 1024 ** 2)
app.cleanup_ctx.append(session)
app.router.add_route("*", "/{tag}/v1/{rest:.*}", handle)
web.run_app(app, port=PORT, access_log=None)
