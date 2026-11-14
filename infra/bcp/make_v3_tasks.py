"""Copy data/bcp_tasks/bcp-* to data/bcp_tasks_v3/ with the BCP method text in the instruction.

v3 = our CLM variant for BCP (not the paper's setup): the "Keep your context small" and
"Always have an answer on disk" sections of infra/bcp/skill/bcp_search_clm/SKILL.md are
inserted before "## Output". Run with BCP_SKILL=bcp_search_ids (tools with block ids,
no method text in the system prompt) and BCP_TASKS=bcp_tasks_v3.
Usage: python infra/bcp/make_v3_tasks.py
"""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC, DST = ROOT / "data" / "bcp_tasks", ROOT / "data" / "bcp_tasks_v3"
skill = (ROOT / "infra/bcp/skill/bcp_search_clm/SKILL.md").read_text()
method = skill[skill.index("## Keep your context small"):].rstrip()
for d in sorted(SRC.glob("bcp-*")):
    out = DST / d.name
    shutil.rmtree(out, ignore_errors=True)
    shutil.copytree(d, out)
    p = out / "instruction.md"
    t = p.read_text()
    assert "\n## Output" in t, d
    p.write_text(t.replace("\n## Output", "\n" + method + "\n\n## Output", 1))
print(f"wrote {len(list(DST.glob('bcp-*')))} tasks to {DST}")
