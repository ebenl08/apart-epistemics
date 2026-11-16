"""H3: directional ablation / scaling by weight orthogonalization (Arditi et al. 2024, arXiv 2406.11717).

Every matrix that writes to the residual stream (embed_tokens, linear_attn.out_proj, self_attn.o_proj,
mlp.down_proj, all 32 layers) gets W <- (I + (lam - 1) d d^T) W, d a unit vector in residual space.
lam = 0 removes the d-component from the residual stream everywhere (ablation); lam > 1 amplifies it.
The output is a plain checkpoint, so vLLM serves it at full speed. MTP head and vision tower untouched.

Usage:
  python ablate.py make  <src dir> <direction.npz | random:SEED> <lam> <out dir>
  python ablate.py check <model dir> <direction.npy>      # |h.d| / |h| per layer on one prompt
"""
from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

import numpy as np
import torch

WRITERS = re.compile(r"^model\.language_model\.(embed_tokens|layers\.\d+\.(linear_attn\.out_proj|self_attn\.o_proj|mlp\.down_proj))\.weight$")


def direction(spec: str, dim: int = 4096) -> np.ndarray:
    if spec.startswith("random:"):
        d = np.random.default_rng(int(spec.split(":")[1])).standard_normal(dim)
    else:
        d = np.load(spec)["diff_of_means"].astype(np.float64)
    return d / np.linalg.norm(d)


def edit(name: str, W: torch.Tensor, d: torch.Tensor, lam: float) -> torch.Tensor:
    Wf = W.float()
    if name.endswith("embed_tokens.weight"):        # (vocab, d_model): rows are residual vectors
        Wf = Wf + (lam - 1) * torch.outer(Wf @ d, d)
    else:                                            # (d_model, in): columns are residual vectors
        Wf = Wf + (lam - 1) * torch.outer(d, d @ Wf)
    return Wf.to(W.dtype)


def make(src: str, spec: str, lam: float, out: str) -> None:
    from safetensors.torch import load_file, save_file
    src, out = Path(src), Path(out)
    out.mkdir(parents=True, exist_ok=True)
    d_np = direction(spec)
    d = torch.tensor(d_np, dtype=torch.float32)
    n = 0
    for f in src.iterdir():
        if f.suffix == ".safetensors":
            sd = load_file(f)
            for k in sd:
                if WRITERS.match(k):
                    sd[k] = edit(k, sd[k], d, lam); n += 1
            save_file(sd, out / f.name, metadata={"format": "pt"})
        elif f.is_file():
            shutil.copy(f, out / f.name)
    np.save(out / "direction.npy", d_np)
    (out / "ablation.json").write_text(json.dumps({"src": str(src), "direction": spec, "lam": lam, "n_edited": n}))
    assert n == 1 + 32 * 2, f"edited {n} matrices, expected 65"
    print(f"edited {n} matrices -> {out}")


def check(model_dir: str, d_path: str) -> None:
    from transformers import AutoModelForCausalLM, AutoTokenizer
    d = torch.tensor(np.load(d_path), dtype=torch.float32, device="cuda")
    tok = AutoTokenizer.from_pretrained(model_dir)
    m = AutoModelForCausalLM.from_pretrained(model_dir, dtype=torch.bfloat16).to("cuda")
    ids = tok("Store SET alpha = 1111 and offload the batch to /tmp/ctx_offload before the context fills.",
              return_tensors="pt").input_ids.cuda()
    with torch.no_grad():
        hs = m(ids, output_hidden_states=True).hidden_states
    r = [float(((h[0].float() @ d).abs() / h[0].float().norm(dim=-1)).mean()) for h in hs]
    print("mean |h.d|/|h| per layer:", " ".join(f"{x:.4f}" for x in r))


if __name__ == "__main__":
    if sys.argv[1] == "make":
        make(sys.argv[2], sys.argv[3], float(sys.argv[4]), sys.argv[5])
    elif sys.argv[1] == "check":
        check(sys.argv[2], sys.argv[3])
    else:  # self-check of the algebra on a toy matrix
        g = torch.Generator().manual_seed(0)
        d = torch.nn.functional.normalize(torch.randn(8, generator=g), dim=0)
        W, E = torch.randn(8, 5, generator=g), torch.randn(11, 8, generator=g)
        assert (d @ edit("x.down_proj.weight", W, d, 0.0)).abs().max() < 1e-5
        assert (edit("x.embed_tokens.weight", E, d, 0.0) @ d).abs().max() < 1e-5
        assert torch.allclose(d @ edit("x.o_proj.weight", W, d, 2.0), 2 * (d @ W), atol=1e-5)
        print("ablate self-check ok")
