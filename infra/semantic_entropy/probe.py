"""M6 Part 3: linear probes for semantic entropy on the 9B residual stream (plan Part 3).

  dump <prefix>      clm-env: logged request/response per point -> runs/m6-probe/reqs/.
  extract <prefix>   GPU: HF forward pass per decision point, save residual stream at
                     TBG (last prompt token) and SLT (last token of the logged response), all layers.
  fit <prefix>       CPU: probes with 5-fold group-by-trial CV, controls, best-layer direction.

Run with /root/envs/vllm-env/bin/python (transformers + torch + fla).
"""
from __future__ import annotations

import glob
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path("/workspace/apart-epistemics")
SE = ROOT / "runs/m6-se"
OUT = ROOT / "runs/m6-probe"
MODEL = os.environ.get("M6_MODEL", "Qwen/Qwen3.5-9B")  # 9B-RL: /root/models/clm-9b-rl/converted


def points(prefix: str) -> list[dict]:
    rows = []
    for f in sorted(glob.glob(str(SE / f"{prefix}__*.jsonl"))):
        if f.endswith(".samples.jsonl"):
            continue
        rows += [json.loads(x) for x in open(f)]
    return rows


def dump_requests(prefix: str) -> None:
    """clm-env step: write each point's logged request/response to runs/m6-probe/reqs/<trial>.json
    (the vllm-env used for extraction has no harbor/litellm, so it cannot run collect.load_turns)."""
    from collect import load_turns
    (OUT / "reqs").mkdir(parents=True, exist_ok=True)
    by: dict[str, set] = {}
    for r in points(prefix):
        by.setdefault(r["trial"], set()).add(r["t"])
    for trial, ts in by.items():
        T = {t.k: t for t in load_turns(ROOT / "runs/m5-lmlog" / f"{trial}.jsonl")}
        (OUT / "reqs" / f"{trial}.json").write_text(json.dumps(
            {str(k): {"req": T[k].req, "resp": T[k].resp} for k in sorted(ts)}))


def extract(prefix: str) -> None:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(MODEL)
    model = AutoModelForCausalLM.from_pretrained(MODEL, dtype=torch.bfloat16).to("cuda")
    model.eval()
    OUT.mkdir(parents=True, exist_ok=True)
    P = points(prefix)
    by_trial: dict[str, list[dict]] = {}
    for r in P:
        by_trial.setdefault(r["trial"], []).append(r)
    mism = 0
    for trial, rows in by_trial.items():
        out = OUT / f"{trial}.npz"
        if out.exists():
            continue
        L = json.loads((OUT / "reqs" / f"{trial}.json").read_text())
        tbg, slt, meta = [], [], []
        t0 = time.time()
        layers = model.model.layers if hasattr(model.model, "layers") else model.model.language_model.layers
        for r in rows:
            req, resp = L[str(r["t"])]["req"], L[str(r["t"])]["resp"]
            kw = req.get("chat_template_kwargs") or {}
            ids = tok.apply_chat_template(norm_msgs(req["messages"]), tools=req.get("tools"), add_generation_prompt=True,
                                          tokenize=True, **kw)
            ids = list(ids["input_ids"] if hasattr(ids, "keys") else ids)
            want = resp["usage"]["prompt_tokens"]
            if len(ids) != want:
                mism += 1
            msg = dict(resp["choices"][0]["message"])
            if msg.get("reasoning") and not msg.get("reasoning_content"):
                msg["reasoning_content"] = msg["reasoning"]
            msg["content"] = msg.get("content") or ""
            full = tok.apply_chat_template(norm_msgs(req["messages"] + [msg]), tools=req.get("tools"), tokenize=True, **kw)
            full = list(full["input_ids"] if hasattr(full, "keys") else full)
            i_tbg = len(ids) - 1
            i_slt = len(full) - 1
            # the template closes the turn with <|im_end|>\n: use the last token before it
            while i_slt > i_tbg and tok.decode([full[i_slt]]).strip() in ("", "<|im_end|>"):
                i_slt -= 1
            cap: list = []
            def hook(_m, _i, o):
                h = o[0] if isinstance(o, tuple) else o
                cap.append(torch.stack([h[0, i_tbg], h[0, i_slt]]).float().cpu())
            hs = [l.register_forward_hook(hook) for l in layers]
            try:
                with torch.no_grad():
                    model.model(torch.tensor([full], device="cuda"))
            finally:
                for h in hs:
                    h.remove()
            A = torch.stack(cap).numpy().astype(np.float16)            # (layers, 2, d)
            tbg.append(A[:, 0]); slt.append(A[:, 1])
            meta.append({"t": r["t"], "n_prompt": len(ids), "logged_prompt": want, "n_full": len(full)})
            torch.cuda.empty_cache()
        np.savez(out, tbg=np.stack(tbg), slt=np.stack(slt), t=np.array([m["t"] for m in meta]),
                 meta=json.dumps(meta))
        print(f"{trial}: {len(rows)} points in {time.time() - t0:.0f}s, prompt-token mismatches so far {mism}", flush=True)


def norm_msgs(msgs: list[dict]) -> list[dict]:
    """As vLLM's server does before templating: tool-call arguments as dicts, not JSON strings."""
    out = []
    for m in msgs:
        m = dict(m)
        if m.get("tool_calls"):
            tcs = []
            for tc in m["tool_calls"]:
                tc = json.loads(json.dumps(tc))
                a = tc.get("function", {}).get("arguments")
                if isinstance(a, str):
                    try:
                        tc["function"]["arguments"] = json.loads(a)
                    except json.JSONDecodeError:
                        tc["function"]["arguments"] = {}
                tcs.append(tc)
            m["tool_calls"] = tcs
        out.append(m)
    return out


def gamma_star(y: np.ndarray) -> float:
    """Kossen et al.: threshold minimizing summed within-group squared error."""
    best, g = np.inf, 0.0
    for c in np.unique(y)[:-1]:
        lo, hi = y[y <= c], y[y > c]
        e = ((lo - lo.mean()) ** 2).sum() + ((hi - hi.mean()) ** 2).sum()
        if e < best:
            best, g = e, c
    return float(g)


def fit(prefix: str) -> None:
    from scipy.stats import spearmanr
    from sklearn.linear_model import LogisticRegression, Ridge
    from sklearn.metrics import roc_auc_score
    from sklearn.model_selection import GroupKFold
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    P = {(r["trial"], r["t"]): r for r in points(prefix)}
    X = {"tbg": [], "slt": []}
    rows = []
    for f in sorted(glob.glob(str(OUT / f"{prefix}__*.npz"))):
        z = np.load(f)
        trial = Path(f).stem
        for i, t in enumerate(z["t"]):
            r = P[(trial, int(t))]
            rows.append(r)
            X["tbg"].append(z["tbg"][i]); X["slt"].append(z["slt"][i])
    X = {k: np.stack(v).astype(np.float32) for k, v in X.items()}       # (n, layers, d)
    y = np.array([r["se_bits"] for r in rows])
    groups = np.array([r["trial"] for r in rows])
    fill = np.array([r["fill"] for r in rows])
    tidx = np.array([r["t"] for r in rows], float)
    reward = np.array([r["reward"] for r in rows], float)
    g = gamma_star(y)
    yb = (y > g).astype(int)
    lines = [f"# M6 Part 3: SE probes ({prefix})", "",
             f"{len(y)} points, {len(set(groups))} trials, {X['tbg'].shape[1]} hidden-state layers. "
             f"γ* = {g:.3f} bits (Kossen); high-SE share {yb.mean():.2f}. 5-fold GroupKFold by trial; "
             f"layer chosen on inner folds.", ""]
    gkf = GroupKFold(n_splits=5)

    def cv(feat_fn, target, kind, layer_select=True):
        """Outer CV; if layer_select, pick the layer by inner GroupKFold on the training part."""
        pred = np.zeros(len(target))
        layers_used = []
        for tr, te in gkf.split(np.zeros(len(target)), target, groups):
            if layer_select:
                cand = range(0, feat_fn(None).shape[1], 2)
                best, bl = -np.inf, 0
                inner = GroupKFold(n_splits=3)
                for l in cand:
                    s = []
                    for itr, ite in inner.split(tr, target[tr], groups[tr]):
                        m = model(kind).fit(feat_fn(l)[tr][itr], target[tr][itr])
                        s.append(score(kind, target[tr][ite], out(m, kind, feat_fn(l)[tr][ite])))
                    if np.mean(s) > best:
                        best, bl = np.mean(s), l
                layers_used.append(bl)
                F = feat_fn(bl)
            else:
                F = feat_fn(None)
            m = model(kind).fit(F[tr], target[tr])
            pred[te] = out(m, kind, F[te])
        return score(kind, target, pred), layers_used

    def model(kind):
        return make_pipeline(StandardScaler(), LogisticRegression(C=0.05, max_iter=2000) if kind == "clf" else Ridge(alpha=1000.0))

    def out(m, kind, F):
        return m.predict_proba(F)[:, 1] if kind == "clf" else m.predict(F)

    def score(kind, t, p):
        if kind == "clf":
            return roc_auc_score(t, p) if 0 < t.sum() < len(t) else np.nan
        return spearmanr(t, p).statistic

    base = np.c_[fill, tidx]
    lines += ["| target | features | score | layers chosen (per fold) |", "|---|---|---|---|"]
    res = {}
    for pos in ("tbg", "slt"):
        for name, tgt, kind in (("binary SE > γ*", yb, "clf"), ("continuous SE", y, "reg")):
            s, ls = cv(lambda l, pos=pos: X[pos] if l is None else X[pos][:, l], tgt, kind)
            res[(pos, name)] = (s, ls)
            lines.append(f"| {name} ({'AUROC' if kind == 'clf' else 'Spearman'}) | {pos.upper()} activations | **{s:.3f}** | {ls} |")
    for name, tgt, kind in (("binary SE > γ*", yb, "clf"), ("continuous SE", y, "reg")):
        s, _ = cv(lambda l: base, tgt, kind, layer_select=False)
        lines.append(f"| {name} | control: fill + turn index | {s:.3f} | – |")
        rng = np.random.default_rng(0)
        sh = rng.permutation(tgt)
        s, _ = cv(lambda l: X["tbg"] if l is None else X["tbg"][:, l], sh, kind)
        lines.append(f"| {name} | control: TBG, shuffled labels | {s:.3f} | – |")
    # SE residualized on fill: does the probe find SE beyond context length?
    res_y = y - np.polyval(np.polyfit(fill, y, 2), fill)
    s, ls = cv(lambda l: X["tbg"] if l is None else X["tbg"][:, l], res_y, "reg")
    lines.append(f"| SE residualized on fill (Spearman) | TBG activations | **{s:.3f}** | {ls} |")
    # direct probe for reward (trial outcome) for comparison
    s, ls = cv(lambda l: X["tbg"] if l is None else X["tbg"][:, l], (reward < 0.5).astype(int), "clf")
    lines.append(f"| trial reward < 0.5 (AUROC) | TBG activations | {s:.3f} | {ls} |")
    lines.append("")
    # direction for H3 at the most-chosen TBG layer
    ls = res[("tbg", "binary SE > γ*")][1]
    best = max(set(ls), key=ls.count)
    F = X["tbg"][:, best]
    m = model("clf").fit(F, yb)
    w = m[-1].coef_[0] / m[0].scale_
    dom = F[yb == 1].mean(0) - F[yb == 0].mean(0)
    np.savez(OUT / f"direction-{prefix}.npz", layer=best, probe_w=w, diff_of_means=dom,
             cos=float(w @ dom / np.linalg.norm(w) / np.linalg.norm(dom)))
    lines += [f"Direction for H3 saved: `runs/m6-probe/direction-{prefix}.npz` (TBG layer {best}; "
              f"cos(probe w, diff-of-means) = {float(w @ dom / np.linalg.norm(w) / np.linalg.norm(dom)):.3f}).", ""]
    (OUT / f"probe-{prefix}.md").write_text("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    if sys.argv[1] == "dump":
        sys.path[:0] = [str(ROOT / "context-language-models/clm"), str(ROOT / "infra"), str(ROOT / "infra/semantic_entropy")]
        dump_requests(sys.argv[2])
    else:
        {"extract": extract, "fit": fit}[sys.argv[1]](sys.argv[2])
