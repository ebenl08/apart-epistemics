"""Shared helper: next result id R0001, R0002, ... (counter in /tmp/.bcp_rid)."""
import pathlib
def next_rid() -> str:
    p = pathlib.Path("/tmp/.bcp_rid")
    n = int(p.read_text()) + 1 if p.exists() else 1
    p.write_text(str(n))
    return f"R{n:04d}"
