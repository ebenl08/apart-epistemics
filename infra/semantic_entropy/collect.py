"""M6 semantic entropy collection. Plan: .agent/instruction-semantic-entropy.md Part 1.

Subcommands (each resumable, one trial log per call unless noted):
  replay  <log.jsonl>            Pass 1: re-run logged commands, check outputs (Gate A).
  points  <log.jsonl>...         Step 5: choose decision points.
  sample  --api URL <log.jsonl>  Pass 2: K samples per point from the model server.
  execute <log.jsonl>            Pass 3: run each sample on a copy of the turn-t sandbox, label, SE.

Run on the pod with the clm-env venv and
PYTHONPATH=/workspace/apart-epistemics/context-language-models/clm:/workspace/apart-epistemics/infra:/workspace/apart-epistemics/infra/semantic_entropy
"""
from __future__ import annotations

import argparse
import asyncio
import copy
import gzip
import hashlib
import json
import logging
import math
import os
import random
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path

ROOT = Path("/workspace/apart-epistemics")
OUT = ROOT / "runs/m6-se"
ROOTS = Path(os.environ.get("M6_ROOTS", "/root/m6roots"))   # container disk: proot on the volume is slow
os.environ.setdefault("CHROOT_ROOT_DIR", str(ROOTS / "chroots"))
K = 10
MAX_POINTS = 40
STAY_PER_BIN = 5
EXCLUDE = ("tmp/.live_ctx", "tmp/.bash_ctx_state")   # harness files, not the model's data

from entropy import cluster, label_blocks, outcome_key, se_bits, se_weighted_bits  # noqa: E402

logging.basicConfig(level=logging.WARNING)


# ---------------------------------------------------------------- Step 2: turns
@dataclass
class Turn:
    k: int
    line: int
    req: dict
    resp: dict
    pending: dict        # the assistant message as the harness appended it (from the next request)
    cmd: str
    tool_content: str
    fill: float
    turn_type: str


def load_turns(log: Path) -> list[Turn]:
    from clm_harness.clm_agent.harness import _extract_tool_call
    # The proxy writes a line when the call completes; a slow call that was retried lands
    # after its retry. Call order = request start time (the harness is sequential).
    L = sorted((json.loads(x) for x in open(log)), key=lambda x: x["t0"])
    turns: list[Turn] = []
    for i, x in enumerate(L):
        if x.get("status") != 200 or not (x.get("response") or {}).get("choices"):
            continue
        msg = copy.deepcopy(x["response"]["choices"][0]["message"])
        a = _extract_tool_call(msg)
        if a["type"] != "command" and a["type"] != "done":
            continue
        # it ran iff a later request carries a tool message with this call's id
        hit = None
        for y in L[i + 1:]:
            ms = (y.get("request") or {}).get("messages") or []
            j = next((j for j, m in enumerate(ms) if m.get("role") == "tool"
                      and m.get("tool_call_id") == a["tool_call_id"]), None)
            if j:
                hit = (ms, j)
                break
        if hit is None:
            continue
        ms, j = hit
        tc = ms[j]["content"]
        tc = tc if isinstance(tc, str) else "".join(p.get("text", "") for p in tc)
        turns.append(Turn(
            k=len(turns), line=i, req=x["request"], resp=x["response"], pending=ms[j - 1],
            cmd=a.get("command") or "", tool_content=tc,
            fill=x["response"]["usage"]["prompt_tokens"] / 32768,
            turn_type="context_edit_turn" if "edit applied" in tc else "context_stay_turn"))
    return turns


def trial_of(log: Path) -> tuple[str, str]:
    run, task = log.stem.split("__")
    return run, task


# ---------------------------------------------------------------- Step 3: harness objects
def make_agent(tmp: Path):
    from clm_contextbench.clm_stream import ClmStream
    return ClmStream(logs_dir=tmp, model_name="openai/qwen35-9b", skill="clm",
                     api_base="http://localhost:8010/v1")


def make_env(task: str, root: Path | None = None):
    from chroot_env import ChrootEnvironment
    from harbor.models.task.task import Task
    from harbor.models.trial.paths import TrialPaths
    t = Task(ROOT / "data/cb_tasks" / task)
    tp = TrialPaths(Path(tempfile.mkdtemp(prefix="m6tp_")))
    env = ChrootEnvironment(environment_dir=t.paths.environment_dir, environment_name=t.short_name,
                            session_id=f"{task}__m6", trial_paths=tp, task_env_config=t.config.environment)
    if root is not None:
        env._root_dir = root
    return env


async def fresh_trial(task: str):
    """Agent + sandbox exactly as harbor set them up before the first LM call."""
    tmp = Path(tempfile.mkdtemp(prefix="m6logs_"))
    agent = make_agent(tmp)
    env = make_env(task)
    await env.start(force_build=False)
    await agent.setup(env)
    await agent.cb_setup(env, budget=agent.context_budget_tokens,
                         reserve=agent.context_budget_reserve_tokens)
    return agent, env


async def run_turn(agent, env, turn: Turn, cmd: str | None = None, pending: dict | None = None,
                   msgs: list | None = None):
    msgs = copy.deepcopy(turn.req["messages"]) if msgs is None else msgs
    agent._budget.calibrate(turn.resp, msgs)
    obs = await agent._ctx.step(cmd if cmd is not None else turn.cmd, msgs, environment=env,
                                pending=pending if pending is not None else turn.pending)
    return obs, msgs


# ---------------------------------------------------------------- Pass 1: replay
async def replay(log: Path) -> dict:
    run, task = trial_of(log)
    out = OUT / f"{log.stem}.replay.json"
    if out.exists():
        return json.loads(out.read_text())
    turns = load_turns(log)
    agent, env = await fresh_trial(task)
    rec = {"trial": log.stem, "n_turns": len(turns), "diverged_at": None, "stdout_only_mismatch": []}
    try:
        for t in turns:
            obs, _ = await run_turn(agent, env, t)
            got = obs.render()
            if got != t.tool_content:
                if t.tool_content.startswith(obs.stdout_block):
                    rec["stdout_only_mismatch"].append(t.k)   # harness note/readout differs, disk same
                    continue
                rec.update(diverged_at=t.k, cmd=t.cmd[:500], want=t.tool_content[:800], got=got[:800])
                break
    finally:
        await env.stop(delete=True)
    rec["digest"] = digest()
    OUT.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rec, indent=1))
    return rec


def digest() -> str:
    try:
        s = (ROOT / "runs/logs/setup-pod.log").read_text()
        i = s.index("rootfs ok sha256:")
        return s[i + 10:i + 10 + 71]
    except Exception:  # noqa: BLE001
        return "unknown"


# ---------------------------------------------------------------- Step 5: points
def choose_points(log: Path) -> list[int]:
    out = OUT / f"{log.stem}.points.json"
    if out.exists():
        return json.loads(out.read_text())
    rep = json.loads((OUT / f"{log.stem}.replay.json").read_text())
    lim = rep["diverged_at"] if rep["diverged_at"] is not None else rep["n_turns"]
    turns = [t for t in load_turns(log) if t.k < lim]
    rng = random.Random(int(hashlib.sha256(log.stem.encode()).hexdigest()[:8], 16))
    edits = [t for t in turns if t.turn_type == "context_edit_turn"]
    stays = [t for t in turns if t.turn_type == "context_stay_turn"]
    pick_stay = []
    for lo in (0, .25, .5, .75):
        b = [t for t in stays if lo <= t.fill < lo + .25 or (lo == .75 and t.fill >= 1)]
        pick_stay += rng.sample(b, min(STAY_PER_BIN, len(b)))
    pts = edits + pick_stay
    if len(pts) > MAX_POINTS:
        top = [t for t in edits if t.fill >= .75]
        rest = [t for t in pts if t not in top]
        pts = top[:MAX_POINTS] + rng.sample(rest, max(0, MAX_POINTS - len(top)))
    ks = sorted(t.k for t in pts)
    out.write_text(json.dumps(ks))
    return ks


# ---------------------------------------------------------------- Pass 2: sample
def post(api: str, body: dict) -> dict:
    r = urllib.request.Request(api.rstrip("/") + "/chat/completions", data=json.dumps(body).encode(),
                               headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(r, timeout=3600))


def parse_choice(ch: dict) -> dict:
    from clm_harness.clm_agent.harness import _extract_tool_call
    msg = copy.deepcopy(ch["message"])
    a = _extract_tool_call(msg)
    lp = (ch.get("logprobs") or {}).get("content") or []
    status = {"command": "ok", "done": "ok"}.get(a["type"], a["type"])
    return {"status": status, "cmd": a.get("command"), "message": msg,
            "logprob_norm": (sum(x["logprob"] for x in lp) / len(lp)) if lp else None,
            "finish_reason": ch.get("finish_reason")}


async def sample(log: Path, api: str, conc: int) -> None:
    out = OUT / f"{log.stem}.samples.jsonl"
    done = {json.loads(x)["t"] for x in open(out)} if out.exists() else set()
    turns = load_turns(log)
    pts = [k for k in choose_points(log) if k not in done]
    sem = asyncio.Semaphore(conc)

    async def one(k: int):
        async with sem:
            t = turns[k]
            body = copy.deepcopy(t.req)
            body.update(n=K, logprobs=True,
                        seed=int(hashlib.sha256(f"{log.stem}:{k}".encode()).hexdigest()[:8], 16) % 2**31)
            r = await asyncio.to_thread(post, api, body)
            pt, want = r["usage"]["prompt_tokens"], t.resp["usage"]["prompt_tokens"]
            rec = {"t": k, "prompt_tokens": pt, "logged_prompt_tokens": want,
                   "samples": [parse_choice(c) for c in r["choices"]]}
            with open(out, "a") as f:
                f.write(json.dumps(rec) + "\n")
            if pt != want:
                print(f"PROMPT MISMATCH {log.stem} t={k}: {pt} vs {want}", flush=True)

    await asyncio.gather(*(one(k) for k in pts))
    have = {json.loads(x)["t"] for x in open(out)} if out.exists() else set()
    if set(choose_points(log)) <= have:
        (OUT / f"{log.stem}.samples.done").touch()


# ---------------------------------------------------------------- Pass 3: execute
def data_files(root: Path) -> dict[str, bytes]:
    out = {}
    for p in [q for d in ("tmp", "app") if (root / d).is_dir() for q in (root / d).rglob("*")]:
        rel = str(p.relative_to(root))
        if p.is_file() and not p.is_symlink() and not rel.startswith(EXCLUDE):
            try:
                out[rel] = p.read_bytes()
            except OSError:
                pass
    return out


def written_since(root: Path, marker: float) -> str:
    parts = []
    for p in root.rglob("*"):
        rel = str(p.relative_to(root))
        if rel.startswith(("proc", "sys", "dev", ".se_marker")) or rel.startswith(EXCLUDE):
            continue
        try:
            if p.is_file() and not p.is_symlink() and p.stat().st_mtime >= marker:
                parts.append(p.read_text(errors="replace"))
        except OSError:
            pass
    return "\n".join(parts)


def rsync(src: Path, dst: Path) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    subprocess.run(["rsync", "-a", "--delete", f"{src}/", f"{dst}/"], check=True)


async def label_command(agent_factory, env_factory, root: Path, t: Turn, cmd: str, pending: dict,
                        before_text: str, data_before: dict[str, bytes]):
    from clm_harness.context_utils.context_string import render_editable
    agent = agent_factory()
    agent._budget.tok_ratio = agent_factory.ratio
    env = env_factory(root)
    (root / ".se_marker").touch()
    marker = (root / ".se_marker").stat().st_mtime
    obs, msgs = await run_turn(agent, env, t, cmd=cmd, pending=pending)
    after_text = render_editable(msgs, 2)
    rc = obs.result.return_code
    if rc != 0 and not obs.ctx_changed:
        return "invalid", None, False, rc, msgs
    labels = label_blocks(before_text, after_text, written_since(root, marker))
    after_all = b"\n".join(data_files(root).values())
    clobber = any(v and v not in after_all for v in data_before.values())
    return "ok", labels, clobber, rc, msgs


def as_pending(message: dict) -> dict:
    """A sampled vLLM message in the shape the harness appends (reasoning_content)."""
    m = dict(message)
    if m.get("reasoning") and not m.get("reasoning_content"):
        m["reasoning_content"] = m.pop("reasoning")
    m["content"] = m.get("content") or ""
    return m


async def execute(log: Path) -> None:
    from clm_harness.context_utils.context_string import render_editable
    run, task = trial_of(log)
    out = OUT / f"{log.stem}.jsonl"
    if out.exists():
        return
    samples = {json.loads(x)["t"]: json.loads(x) for x in open(OUT / f"{log.stem}.samples.jsonl")}
    turns = load_turns(log)
    pts = set(choose_points(log))
    meta = trial_meta(run, task)
    agent, env = await fresh_trial(task)
    main = env.root
    work = ROOTS / "work" / log.stem
    tmp = Path(tempfile.mkdtemp(prefix="m6x_"))

    def agent_factory():
        return make_agent(tmp)
    rows, gate_b = [], []
    try:
        for t in turns:
            if t.k > max(pts):
                break
            if t.k in pts and t.k in samples:
                agent_factory.ratio = agent._budget.tok_ratio
                before_text = render_editable(t.req["messages"], 2)
                data_before = data_files(main)
                keys, ss, lw = [], [], {}
                for s in samples[t.k]["samples"]:
                    if s["status"] != "ok":
                        key = s["status"]
                        rc = None
                    else:
                        rsync(main, work)
                        try:
                            st, labels, clob, rc, _ = await label_command(
                                agent_factory, lambda r: make_env(task, r), work, t, s["cmd"],
                                as_pending(s["message"]), before_text, data_before)
                            key = outcome_key(st, labels, clob)
                        except Exception as e:  # noqa: BLE001
                            key, rc = "error", repr(e)[:200]
                    keys.append(key)
                    ss.append({"key": key, "rc": rc, "cmd": (s.get("cmd") or "")[:300],
                               "logprob_norm": s.get("logprob_norm"), "finish": s.get("finish_reason")})
                    if s.get("logprob_norm") is not None:
                        lw[key] = lw.get(key, 0.0) + math.exp(s["logprob_norm"])
                # Gate B: the logged command, labelled the same way, must reproduce req_{t+1}
                rsync(main, work)
                st, labels, clob, _, msgs = await label_command(
                    agent_factory, lambda r: make_env(task, r), work, t, t.cmd, t.pending,
                    before_text, data_before)
                logged_key = outcome_key(st, labels, clob)
                nxt = turns[t.k + 1].req["messages"] if t.k + 1 < len(turns) else None
                gb = None
                if nxt is not None:
                    gb = render_editable(msgs, 2) == render_editable(nxt[:len(msgs)], 2)
                    gate_b.append(gb)
                counts = cluster(keys)
                rows.append({**meta, "t": t.k, "fill": round(t.fill, 4), "turn_type": t.turn_type,
                             "logged_key": logged_key, "gate_b": gb, "clusters": counts,
                             "se_bits": round(se_bits(list(counts.values())), 4),
                             "se_weighted_bits": round(se_weighted_bits(lw), 4) if lw else None,
                             "n_invalid": keys.count("invalid"), "n_no_command": keys.count("no_tool_call"),
                             "n_error": keys.count("error"), "samples": ss, "rootfs_digest": digest()})
            await run_turn(agent, env, t)
    finally:
        await env.stop(delete=True)
        shutil.rmtree(work, ignore_errors=True)
    out.write_text("".join(json.dumps(r) + "\n" for r in rows))
    print(f"{log.stem}: {len(rows)} points, gate B {sum(bool(g) for g in gate_b)}/{len(gate_b)}", flush=True)


def trial_meta(run: str, task: str) -> dict:
    d = ROOT / "runs" / run.replace("-lmlog", "") / "trials" / task
    reward = None
    try:
        r = json.loads((d / "result.json").read_text())
        reward = (r.get("verifier_result") or {}).get("rewards", {}).get("reward")
    except Exception:  # noqa: BLE001
        pass
    fam, lvl, seed = task.rsplit("-", 2)[0], task.rsplit("-", 2)[1], int(task.rsplit("seed", 1)[1])
    return {"trial": f"{run}__{task}", "model": run, "family": fam, "level": lvl, "seed": seed,
            "reward": reward}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["replay", "points", "sample", "execute", "turns"])
    ap.add_argument("logs", nargs="+", type=Path)
    ap.add_argument("--api", default="http://localhost:8010/v1")
    ap.add_argument("--conc", type=int, default=8)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    for log in a.logs:
        if a.cmd == "turns":
            ts = load_turns(log)
            print(log.stem, len(ts), "turns,", sum(t.turn_type == "context_edit_turn" for t in ts), "edit")
        elif a.cmd == "replay":
            r = asyncio.run(replay(log))
            print(log.stem, {k: r[k] for k in ("n_turns", "diverged_at")}, "stdout-only:", len(r["stdout_only_mismatch"]))
        elif a.cmd == "points":
            print(log.stem, len(choose_points(log)), "points")
        elif a.cmd == "sample":
            asyncio.run(sample(log, a.api, a.conc))
        elif a.cmd == "execute":
            asyncio.run(execute(log))


if __name__ == "__main__":
    main()
