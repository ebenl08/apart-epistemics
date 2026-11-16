"""Generate project/Main.dc.html for Figure 1 (placed-element diagram)."""
import pathlib

W, H = 1616, 736
INK, MUTED, ARROW = "#1F2937", "#4B5563", "#6B7280"
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
        f'stroke: {ARROW}; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round{dash}">{defs}<path d="{path}"{me}></path></svg>')


def card(l, t, w, h, fill, border, body, icon="", dashed=False, radius=6):
    bs = "dashed" if dashed else "solid"
    els.append(
        f'<div style="position: absolute; left: {l}px; top: {t}px; width: {w}px; height: {h}px; box-sizing: border-box; padding: 10px 12px; '
        f'display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 6px; text-align: center; '
        f'background: {fill}; border: 1.5px {bs} {border}; border-radius: {radius}px; color: {INK}; '
        f'font-size: 15px; line-height: 20px">{icon}<span>{body}</span></div>')


def label(l, t, w, text, color=MUTED, size=13, weight=500):
    els.append(f'<div style="position: absolute; left: {l}px; top: {t}px; width: {w}px; text-align: center; font-size: {size}px; '
               f'line-height: 16px; font-weight: {weight}; color: {color}">{text}</div>')


def ico(paths, color):
    return (f'<svg aria-hidden="true" width="30" height="30" viewBox="0 0 24 24" style="fill: none; stroke: {color}; stroke-width: 1.8; '
            f'stroke-linecap: round; stroke-linejoin: round; flex: none">{paths}</svg>')


ROBOT = '<rect x="5" y="8" width="14" height="11" rx="4"/><circle cx="9.5" cy="13" r="1.3"/><circle cx="14.5" cy="13" r="1.3"/><path d="M12 8V5"/><circle cx="12" cy="4" r="1.2"/><path d="M10 16.5h4"/>'
FILE = '<path d="M7 3h7l4 4v14H7z"/><path d="M14 3v4h4"/><path d="M9.5 11h6M9.5 14h6M9.5 17h4"/>'
FOLDER = '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path d="M9 13h6"/>'
GEAR = '<circle cx="12" cy="12" r="3"/><path d="M12 3v2.5M12 18.5V21M3 12h2.5M18.5 12H21M5.6 5.6l1.8 1.8M16.6 16.6l1.8 1.8M5.6 18.4l1.8-1.8M16.6 7.4l1.8-1.8"/>'
WAVE = '<path d="M3 9c2-2 4-2 6 0s4 2 6 0 4-2 6 0"/><path d="M3 15c2-2 4-2 6 0s4 2 6 0 4-2 6 0"/>'


def dots(colors):
    return "".join(f'<span style="display: inline-block; width: 8px; height: 8px; margin: 0 1.5px; border-radius: 50%; background: {c}"></span>' for c in colors)


# ---------------- Panel (a): the CLM loop ----------------
els.append(f'<div style="position: absolute; left: 64px; top: 56px; font-size: 20px; line-height: 28px; font-weight: 700; color: {INK}">(a) The CLM loop</div>')
els.append(f'<div style="position: absolute; left: 856px; top: 56px; font-size: 20px; line-height: 28px; font-weight: 700; color: {INK}">(b) Measuring decision uncertainty</div>')

card(64, 152, 176, 96, "#EEF2F8", "#4C72B0", "<b>Model</b><br>one bash command per turn")
card(332, 152, 176, 96, "#FFFFFF", "#9CA3AF", "<b>Context file</b><br>blocks kept, edited, offloaded or deleted")
card(600, 152, 176, 96, "#FFFFFF", "#9CA3AF", "<b>Disk</b><br>offloaded batches")
card(332, 400, 176, 96, "#FFFFFF", "#9CA3AF", "<b>Harness</b><br>reads the file back")
card(600, 400, 176, 96, "#FFFFFF", "#9CA3AF", "<b>Data stream</b><br>0.5× to 24× the budget")
card(332, 584, 444, 72, "#FBEEEE", "#C44E52", '<b style="color: #A33A3E">Budget wall</b>: context reaches 32k tokens, the trial ends')

arrow(240, 200, 91, "r", "From Model to Context file, by one command")
label(250, 172, 72, "command")
arrow(508, 200, 91, "r", "From Context file to Disk, when a batch is offloaded")
label(522, 172, 64, "offload")
arrow(420, 248, 151, "d", "From Context file to Harness, edited context read back")
label(432, 304, 96, "edited<br>context", size=13)
arrow(152, 448, 180, "l", "", head=False)
arrow(152, 249, 199, "u", "From Harness back to Model, as the next prompt")
label(164, 340, 80, "next<br>prompt")
arrow(688, 249, 151, "u", "From Data stream to Disk, new batches arrive")
label(700, 304, 64, "new<br>batches")
arrow(420, 496, 87, "d", "From Harness to Budget wall, if the context is full")
label(432, 532, 56, "if full")

# ---------------- Panel (b): the measurement ----------------
G, Y = "#FFFFFF", "#9CA3AF"
B, BB = "#EEF2F8", "#4C72B0"
# row A: replay, then pause and snapshot
card(856, 120, 300, 64, G, Y, "<b>Replay</b> logged commands 1 … t−1<br>in a fresh sandbox, no model")
card(1252, 120, 292, 64, G, Y, "<b>Pause at decision point t</b><br>snapshot the disk (pristine)")
arrow(1156, 152, 95, "r", "From Replay to Pause at decision point t")
# one to many: snapshot to the ten samples
arrow(1398, 184, 44, "d", "", head=False)
arrow(912, 228, 576, "r", "", head=False)
for k, cx in enumerate((912, 1056, 1344, 1488)):
    arrow(cx, 228, 43, "d", f"From the snapshot to sample {(1, 2, 9, 10)[k]}")
label(1144, 236, 112, "10 replies,<br>same prompt", size=12)
for left, name in ((856, "Sample 1"), (1000, "Sample 2"), (1288, "Sample 9"), (1432, "Sample 10")):
    card(left, 272, 112, 72, B, BB, f"<b>{name}</b><br>own copy")
card(1144, 272, 112, 72, "#FFFFFF", "#D1D5DB", "<b>…</b>")
# many to one: samples to grouping
for cx in (912, 1056, 1344, 1488):
    arrow(cx, 344, 48, "d", "", head=False)
arrow(912, 392, 576, "r", "", head=False)
arrow(1200, 392, 31, "d", "From the ten outcome keys to Group equal outcome keys")
label(1100, 356, 200, "outcome key per sample", size=12)
# row C: group, entropy, continue
card(1088, 424, 224, 88, G, Y, "<b>Group equal outcome keys</b><br>" + dots(["#DD8452"] * 6) + " " + dots(["#4C72B0"] * 3) + " " + dots(["#55A868"]))
card(856, 424, 136, 88, "#FBF0E7", "#DD8452", "<b>Semantic entropy</b><br>−Σ p log₂ p")
card(1408, 424, 136, 88, G, Y, "<b>Continue replay</b><br>with logged cmd t")
arrow(993, 468, 95, "l", "From Group equal outcome keys to Semantic entropy")
arrow(1312, 468, 95, "r", "From Group equal outcome keys to Continue replay with logged cmd t")
label(1328, 440, 64, "then", size=12)
label(856, 400, 136, "Experiment 2", color="#B8652F", size=12, weight=700)
# probe
card(1088, 584, 360, 72, B, BB, "<b>Linear probe</b> on the residual stream<br>at the last token of prompt t, no sampling", dashed=True)
arrow(924, 620, 164, "l", "", head=False, dashed=True)
arrow(924, 513, 107, "u", "From Linear probe to Semantic entropy, predicts it before generation", dashed=True)
label(936, 552, 96, "predicts<br>SE &gt; 0")
label(1088, 664, 360, "Experiment 3", color="#4C72B0", size=12, weight=700)

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
pathlib.Path(__file__).with_name("project").joinpath("Main.dc.html").write_text(html)
