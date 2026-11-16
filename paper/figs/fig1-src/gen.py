"""Generate project/Main.dc.html for Figure 1, compact print layout (W=1184 px -> 5.5 in; 20 px ~ 6.7 pt)."""
import pathlib

W, H = 1184, 640
INK, MUTED, ARROW = "#1F2937", "#374151", "#6B7280"
G, Y = "#FFFFFF", "#9CA3AF"          # neutral card
B, BB = "#EEF2F8", "#4C72B0"         # model-side accent (blue)
O, OB = "#FBF0E7", "#DD8452"         # semantic entropy (orange)
R, RB = "#FBEEEE", "#C44E52"         # budget wall (red)
els, arrows = [], []
mid = [0]


def arrow(x, y, n, d, label, head=True, dashed=False):
    """Straight segment. (x,y) = left end (horizontal) / top end (vertical). d in r,l,u,d."""
    h = 4 if head else 0
    dash = "; stroke-dasharray: 6 6" if dashed else ""
    if d in "rl":
        box = f"left: {x}px; top: {y-4}px; width: {n}px; height: 8px"
        wh, vb = f'width="{n}" height="8"', f"0 0 {n} 8"
        path = f"M 0 4 L {n-h} 4" if d == "r" else f"M {n} 4 L {h} 4"
    else:
        box = f"left: {x-4}px; top: {y}px; width: 8px; height: {n}px"
        wh, vb = f'width="8" height="{n}"', f"0 0 8 {n}"
        path = f"M 4 0 L 4 {n-h}" if d == "d" else f"M 4 {n} L 4 {h}"
    a11y = f'role="img" aria-label="{label}"' if label else 'aria-hidden="true"'
    defs = me = ""
    if head:
        mid[0] += 1
        i = mid[0]
        defs = (f'<defs><marker id="dc-arrow-head-filled-{i}" orient="auto" markerWidth="5" markerHeight="5" refX="2" refY="2" overflow="visible">'
                f'<path d="M0 0 L4 2 L0 4 Z" fill="{ARROW}" stroke="none" style="stroke: none; fill: {ARROW}; fill: context-stroke"/></marker></defs>')
        me = f' marker-end="url(#dc-arrow-head-filled-{i})"'
    arrows.append(
        f'<svg {a11y} {wh} viewBox="{vb}" preserveAspectRatio="none" style="position: absolute; {box}; overflow: visible; fill: none; '
        f'stroke: {ARROW}; stroke-width: 2.5; stroke-linecap: round; stroke-linejoin: round{dash}">{defs}<path d="{path}"{me}></path></svg>')


def card(l, t, w, h, fill, border, title, sub="", dashed=False):
    bs = "dashed" if dashed else "solid"
    body = f"<b>{title}</b>" + (f'<br><span style="font-size: 18px; color: {MUTED}">{sub}</span>' if sub else "")
    els.append(
        f'<div style="position: absolute; left: {l}px; top: {t}px; width: {w}px; height: {h}px; box-sizing: border-box; padding: 6px 8px; '
        f'display: flex; align-items: center; justify-content: center; text-align: center; '
        f'background: {fill}; border: 2px {bs} {border}; border-radius: 6px; color: {INK}; font-size: 20px; line-height: 24px"><span>{body}</span></div>')


def label(l, t, w, text, color=MUTED, weight=500, align="center"):
    els.append(f'<div style="position: absolute; left: {l}px; top: {t}px; width: {w}px; text-align: {align}; font-size: 18px; '
               f'line-height: 20px; font-weight: {weight}; color: {color}">{text}</div>')


def dots(colors):
    return "".join(f'<span style="display: inline-block; width: 10px; height: 10px; margin: 0 2px; border-radius: 50%; background: {c}"></span>' for c in colors)


# titles
for x, t in ((64, "(a) The CLM loop"), (624, "(b) Measuring decision uncertainty")):
    els.append(f'<div style="position: absolute; left: {x}px; top: 40px; font-size: 24px; line-height: 30px; font-weight: 700; color: {INK}">{t}</div>')

# ---------------- Panel (a): the CLM loop (columns x 64 / 256 / 448, w 112; rows y 112 / 264) ----------------
card(64, 112, 112, 72, B, BB, "Model", "1 cmd/turn")
card(256, 112, 112, 72, G, Y, "Context file", "")
card(448, 112, 112, 72, G, Y, "Disk", "offloads")
card(256, 264, 112, 72, G, Y, "Harness", "reads file")
card(448, 264, 112, 72, G, Y, "Stream", "0.5–24×")
card(256, 400, 304, 56, R, RB, '<span style="color: #A33A3E">Budget wall</span>', "")
label(256, 464, 304, "context hits 32k, trial ends")

arrow(176, 148, 79, "r", "From Model to Context file, one command")
label(180, 112, 72, "cmd")
arrow(368, 148, 79, "r", "From Context file to Disk, offload")
label(368, 112, 80, "offload")
arrow(312, 184, 79, "d", "From Context file to Harness, edited context read back")
label(324, 200, 112, "edited<br>context", align="left")
arrow(120, 300, 136, "l", "", head=False)
arrow(120, 185, 115, "u", "From Harness back to Model, as the next prompt")
label(132, 222, 112, "next<br>prompt", align="left")
arrow(504, 185, 79, "u", "From Stream to Disk, new batches")
label(516, 200, 64, "new<br>data", align="left")
arrow(312, 336, 63, "d", "From Harness to Budget wall, if the context is full")
label(324, 356, 80, "if full", align="left")

# ---------------- Panel (b): the measurement (x 624..1120) ----------------
card(624, 112, 216, 64, G, Y, "Replay to point t", "logged cmds only")
card(904, 112, 216, 64, G, Y, "Snapshot disk", "at decision point t")
arrow(840, 144, 63, "r", "From Replay to Snapshot disk")
label(624, 184, 360, "10 samples, same prompt, own disk copy", align="left")
arrow(1012, 176, 32, "d", "", head=False)
arrow(664, 208, 416, "r", "", head=False)
xs = (624, 728, 832, 936, 1040)
names = ("S1", "S2", "…", "S9", "S10")
for x, nm in zip(xs, names):
    arrow(x + 40, 208, 39, "d", "" if nm == "…" else f"From the snapshot to sample {nm[1:]}")
    card(x, 248, 80, 56, B if nm != "…" else G, BB if nm != "…" else "#D1D5DB", nm)
    arrow(x + 40, 304, 32, "d", "", head=False)
arrow(664, 336, 416, "r", "", head=False)
arrow(872, 336, 39, "d", "From the ten outcome keys to Group equal outcome keys")
label(624, 348, 112, "Exp. 2", color="#B8652F", weight=700, align="left")

card(624, 376, 112, 72, O, OB, "SE", "−Σp log₂p")
card(784, 376, 176, 72, G, Y, "Group equal keys", dots(["#DD8452"] * 6 + ["#4C72B0"] * 3 + ["#55A868"]))
card(1008, 376, 112, 72, G, Y, "Continue", "logged cmd t")
arrow(737, 412, 47, "l", "From Group equal keys to SE")
arrow(960, 412, 47, "r", "From Group equal keys to Continue with logged cmd t")
label(960, 380, 48, "then")

card(784, 496, 336, 72, B, BB, "Linear probe", "residual stream at last prompt token", dashed=True)
arrow(680, 532, 104, "l", "", head=False, dashed=True)
arrow(680, 449, 83, "u", "From Linear probe to SE, predicts it before generation", dashed=True)
label(692, 466, 88, "predicts<br>SE &gt; 0", align="left")
label(784, 576, 336, "Exp. 3: no sampling needed", color="#4C72B0", weight=700)

html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Figure 1: CLM loop and uncertainty measurement</title>
<script src="./support.js"></script>
</head>
<body>
<x-dc>
<helmet>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&amp;display=swap">
<style>
body{{margin:0}}
a{{color:#4C72B0}}a:hover{{color:#33507F}}
</style>
</helmet>
<div style="position: relative; width: {W}px; height: {H}px; background: #FFFFFF; font-family: Inter, system-ui, sans-serif; color: {INK}">
{chr(10).join(arrows)}
{chr(10).join(els)}
</div>
</x-dc>
<script type="text/x-dc" data-dc-script data-props='{{"$preview":{{"width":{W},"height":{H}}}}}'>
class Component extends DCLogic {{
renderVals() {{
return {{}};
}}
}}
</script>
</body>
</html>
"""
out = pathlib.Path(__file__).with_name("project")
out.joinpath("Main.dc.html").write_text(html)
# static copy for local rendering to PDF
body = html[html.index('<div style="position: relative'):html.index("</x-dc>")]
font = html[html.index('<link rel="stylesheet"'):html.index('display=swap">') + len('display=swap">')]
pathlib.Path(__file__).with_name("static.html").write_text(
    f'<!doctype html><html><head><meta charset="utf-8">{font}<style>@page{{size:{W}px {H}px;margin:0}}html,body{{margin:0}}</style></head><body>{body}</body></html>')
