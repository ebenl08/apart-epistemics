"""Build a BM25 index over the BrowseComp-Plus corpus (100,195 docs) with bm25s.

Writes $BCP_INDEX_DIR/bm25/ (bm25s index) and $BCP_INDEX_DIR/docs.parquet (docid, url, text in the
index order). Plan: retriever bm25, the BCP paper's standard sparse baseline.
"""
import glob
import os
import time
from pathlib import Path

import bm25s
import pyarrow as pa
import pyarrow.parquet as pq
import Stemmer

ROOT = Path(__file__).resolve().parents[2] / "data" / "bcp"
# Derived artifacts (docs.parquet, bm25/) live on the local disk: the /workspace volume
# has a quota (hit at ~54 GB).
INDEX = Path(os.environ.get("BCP_INDEX_DIR", "/root/bcp_index"))


def main() -> None:
    INDEX.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    tables = [pq.read_table(f, columns=["docid", "url", "text"])
              for f in sorted(glob.glob(str(ROOT / "corpus/data/*.parquet")))]
    docs = pa.concat_tables(tables)
    pq.write_table(docs, INDEX / "docs.parquet")
    texts = docs.column("text").to_pylist()
    print(f"{len(texts)} docs loaded in {time.time() - t0:.0f}s")
    stemmer = Stemmer.Stemmer("english")
    tokens = bm25s.tokenize(texts, stopwords="en", stemmer=stemmer, show_progress=False)
    retriever = bm25s.BM25()
    retriever.index(tokens, show_progress=False)
    retriever.save(str(INDEX / "bm25"))
    print(f"index built in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
