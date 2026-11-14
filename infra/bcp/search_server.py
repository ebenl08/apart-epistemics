"""BM25 search service for BrowseComp-Plus, shared by all trials on this host.

GET /search?q=<query>&k=10   -> {"results": [{"docid", "url", "score", "snippet"}]}
GET /doc?docid=<id>          -> {"docid", "url", "text", "truncated", "n_tokens"}

Plan settings: top_k 10, snippet 512 tokens, reader capped at 8192 tokens (o200k
tokenizer, the harness's token counter). Usage: python search_server.py [--port 8100]
"""
import argparse
import os
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import bm25s
import pyarrow.parquet as pq
import Stemmer
import tiktoken

ROOT = Path(__file__).resolve().parents[2] / "data" / "bcp"
# Derived artifacts (docs.parquet, bm25/) live on the local disk: the /workspace volume
# has a quota (hit at ~54 GB).
INDEX = Path(os.environ.get("BCP_INDEX_DIR", "/root/bcp_index"))
TOP_K, SNIPPET_TOKENS, READER_TOKENS = 10, 512, 8192

enc = tiktoken.get_encoding("o200k_base")
stemmer = Stemmer.Stemmer("english")
lock = threading.Lock()


def _truncate(text: str, n: int) -> tuple[str, bool, int]:
    ids = enc.encode(text, disallowed_special=())
    return (enc.decode(ids[:n]), len(ids) > n, len(ids))


class State:
    def __init__(self) -> None:
        t0 = time.time()
        docs = pq.read_table(INDEX / "docs.parquet")
        self.docids = docs.column("docid").to_pylist()
        self.urls = docs.column("url").to_pylist()
        self.texts = docs.column("text").to_pylist()
        self.by_id = {d: i for i, d in enumerate(self.docids)}
        self.retriever = bm25s.BM25.load(str(INDEX / "bm25"))
        print(f"loaded {len(self.docids)} docs + index in {time.time() - t0:.0f}s", flush=True)

    def search(self, q: str, k: int) -> list[dict]:
        toks = bm25s.tokenize([q], stopwords="en", stemmer=stemmer, show_progress=False)
        with lock:
            idx, scores = self.retriever.retrieve(toks, k=k, show_progress=False)
        out = []
        for i, s in zip(idx[0].tolist(), scores[0].tolist()):
            snippet, _, _ = _truncate(self.texts[i], SNIPPET_TOKENS)
            out.append({"docid": self.docids[i], "url": self.urls[i],
                        "score": round(float(s), 3), "snippet": snippet})
        return out

    def doc(self, docid: str) -> dict | None:
        i = self.by_id.get(docid)
        if i is None:
            return None
        text, trunc, n = _truncate(self.texts[i], READER_TOKENS)
        return {"docid": docid, "url": self.urls[i], "text": text, "truncated": trunc,
                "n_tokens": n}


STATE: State | None = None


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # quiet
        pass

    def _send(self, code: int, obj: dict) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urlparse(self.path)
        p = {k: v[0] for k, v in parse_qs(u.query).items()}
        try:
            if u.path == "/search":
                q = p.get("q", "").strip()
                if not q:
                    return self._send(400, {"error": "empty query"})
                k = max(1, min(int(p.get("k", TOP_K)), 50))
                return self._send(200, {"query": q, "results": STATE.search(q, k)})
            if u.path == "/doc":
                d = STATE.doc(p.get("docid", ""))
                return self._send(200, d) if d else self._send(404, {"error": "no such docid"})
            if u.path == "/health":
                return self._send(200, {"ok": True})
            return self._send(404, {"error": "unknown path"})
        except Exception as e:  # noqa: BLE001
            return self._send(500, {"error": repr(e)})


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8100)
    args = ap.parse_args()
    STATE = State()
    ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()
