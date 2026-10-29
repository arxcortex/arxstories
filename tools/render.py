#!/usr/bin/env python3
"""Arx map-story card renderer.
Usage: python3 render.py spec.json out.png
spec keys: source (path to site screenshot), crop_x (optional; auto-detects panel edge),
pin [x,y] in source pixels (optional), desk, category, headline, dek, location, date,
severity (0-5), brief (str), context (list of str), sources (list of str), stamp (optional)
"""
import base64, html, json, os, subprocess, sys, tempfile
from pathlib import Path
from PIL import Image

HERE = Path(__file__).resolve().parent
FONT_DIR = HERE / "fonts"
FONTS = {
    ("Cormorant Garamond", 500, "normal"): ("@fontsource/cormorant-garamond@5.3.0", "cormorant-garamond-latin-500-normal.woff2"),
    ("Cormorant Garamond", 500, "italic"): ("@fontsource/cormorant-garamond@5.3.0", "cormorant-garamond-latin-500-italic.woff2"),
    ("Cormorant Garamond", 600, "normal"): ("@fontsource/cormorant-garamond@5.3.0", "cormorant-garamond-latin-600-normal.woff2"),
    ("JetBrains Mono", 400, "normal"): ("@fontsource/jetbrains-mono@5.3.0", "jetbrains-mono-latin-400-normal.woff2"),
    ("JetBrains Mono", 500, "normal"): ("@fontsource/jetbrains-mono@5.3.0", "jetbrains-mono-latin-500-normal.woff2"),
}

def ensure_fonts():
    FONT_DIR.mkdir(exist_ok=True)
    for pkg, fn in set(FONTS.values()):
        if (FONT_DIR / fn).exists():
            continue
        with tempfile.TemporaryDirectory() as td:
            try:
                subprocess.run(["npm", "pack", "-s", pkg], cwd=td, check=True, capture_output=True)
                tgz = next(Path(td).glob("*.tgz"))
                subprocess.run(["tar", "xzf", str(tgz)], cwd=td, check=True)
                src = Path(td) / "package" / "files"
                for f in src.glob("*latin-[456]00-*.woff2"):
                    if not f.name.startswith(("cormorant-garamond-latin", "jetbrains-mono-latin")):
                        continue
                    (FONT_DIR / f.name).write_bytes(f.read_bytes())
            except Exception as e:
                print(f"font fetch failed for {pkg}: {e} (falling back to system fonts)", file=sys.stderr)

def font_css():
    out = []
    for (fam, w, st), (_, fn) in FONTS.items():
        p = FONT_DIR / fn
        if p.exists():
            b = base64.b64encode(p.read_bytes()).decode()
            out.append(f"@font-face{{font-family:'{fam}';font-weight:{w};font-style:{st};src:url(data:font/woff2;base64,{b}) format('woff2');}}")
    return "\n".join(out)

def detect_panel_edge(img):
    """Find the copper vertical rule that marks the story panel's left edge."""
    im = img.convert("RGB")
    w, h = im.size
    px = im.load()
    best, best_x = 0, None
    for x in range(int(w * 0.3), w):
        hits = 0
        for y in range(0, h, 2):
            r, g, b = px[x, y]
            if r > 170 and 110 < g < 175 and b < 130 and r - b > 70:
                hits += 1
        frac = hits / (h / 2)
        if frac > best:
            best, best_x = frac, x
    return best_x if best > 0.6 else None

def main():
    spec = json.loads(Path(sys.argv[1]).read_text())
    out = Path(sys.argv[2]).resolve()
    src = Path(spec["source"])
    if not src.is_absolute():
        src = Path(sys.argv[1]).resolve().parent / src
    img = Image.open(src)
    box = spec.get("map_box")
    crop_x = None
    if box:
        img = img.crop(tuple(box))
    else:
        crop_x = spec.get("crop_x") or detect_panel_edge(img)
        if crop_x:
            img = img.crop((0, 0, max(1, crop_x - 4), img.height))
    mw, mh = img.size
    tmp_map = out.parent / (out.stem + ".map.png")
    img.save(tmp_map)
    map_b64 = base64.b64encode(tmp_map.read_bytes()).decode()
    tmp_map.unlink()

    ensure_fonts()
    e = lambda s: html.escape(str(s or ""))
    L = {"brief": "The Brief", "left": "Left Framing", "right": "Right Framing",
         "context": "Context", "sources": "Reporting", **(spec.get("labels") or {})}
    bars = ""
    if spec.get("severity") is not None:
        sev = max(0, min(5, int(spec["severity"])))
        bars = "".join(f'<i class="{"on" if i < sev else ""}"></i>' for i in range(5))
    ctx = "".join(f"<li>{e(c)}</li>" for c in spec.get("context", [])[:4])
    srcs = "".join(f"<span>{e(s)}</span>" for s in spec.get("sources", [])[:4])
    LB, LC, LS = e(L["brief"]), e(L["context"]), e(L["sources"])
    MARK = e(spec.get("mark", "ΛRXCORTEX.IO"))
    BARS = f'<span class="bars">{bars}</span>' if bars else ""
    fr = spec.get("framing") or spec.get("pair") or {}
    framing = ""
    if fr.get("left") or fr.get("right"):
        framing = '<div class="framing">' + "".join(
            f'<div class="fr"><div class="label">{lab}</div><p>{e(fr.get(k))}</p></div>'
            for k, lab in (("left", e(L["left"])), ("right", e(L["right"])))) + "</div>"
    rd = spec.get("reading") or {}
    READING = ""
    if rd.get("text"):
        READING = (f'<div class="reading"><div class="label">{e(rd.get("label", "The Stakes"))}</div>'
                   f'<p>{e(rd["text"])}</p></div>')
    pin = spec.get("pin")
    if pin and box:
        pin = [pin[0] - box[0], pin[1] - box[1]]
    W, H, MAPW = 1600, 900, 820
    GRADES = {
        "ink": "saturate(.85) contrast(1.05) brightness(.92)",
        "copper": "grayscale(1) sepia(.75) saturate(1.6) hue-rotate(-12deg) contrast(1.12) brightness(.78)",
        "mono": "grayscale(1) contrast(1.15) brightness(.8)",
        "none": "none",
    }
    GRADE = GRADES.get(spec.get("grade", "ink"), GRADES["ink"])
    RING = "true" if spec.get("ring", True) else "false"
    zoom = float(spec.get("zoom", 1.05))
    cap = spec.get("caption")
    CAPTION = f'<div class="cap">{e(cap)}</div>' if cap else ""

    page = f"""<!doctype html><html><head><meta charset="utf-8"><style>
{font_css()}
:root{{--ink:#0b0a09;--panel:#0e0d0b;--copper:#d4875a;--copper-dim:#8a5a3c;--brass:#c9a35b;--bone:#ece4d6;--ash:#9a9286;--rule:#3a2c20;}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{width:{W}px;height:{H}px;background:var(--ink);color:var(--bone);font-family:'JetBrains Mono',monospace;overflow:hidden;position:relative}}
.map{{position:absolute;left:0;top:0;width:{MAPW}px;height:{H}px;overflow:hidden;background:#151410}}
.map img{{position:absolute;filter:{GRADE}}}
.cap{{position:absolute;left:28px;bottom:26px;z-index:3;font-size:11px;letter-spacing:.26em;text-transform:uppercase;color:var(--brass);background:rgba(11,10,9,.72);padding:7px 12px;border-left:2px solid var(--copper)}}
.map:after{{content:"";position:absolute;inset:0;background:radial-gradient(ellipse at var(--fx) var(--fy),transparent 20%,rgba(11,10,9,.55) 70%,rgba(11,10,9,.92) 100%),linear-gradient(90deg,transparent 80%,var(--ink));pointer-events:none}}
.ring{{position:absolute;width:64px;height:64px;margin:-32px 0 0 -32px;border:1.5px solid var(--copper);border-radius:50%;z-index:2;box-shadow:0 0 24px rgba(212,135,90,.45)}}
.ring:before{{content:"";position:absolute;inset:-14px;border:1px dashed var(--copper-dim);border-radius:50%}}
.tick{{position:absolute;z-index:2;height:1px;background:var(--copper);width:120px}}
.tag{{position:absolute;z-index:2;font-size:13px;letter-spacing:.18em;color:var(--copper);text-transform:uppercase;background:rgba(11,10,9,.8);padding:6px 10px;border:1px solid var(--copper-dim)}}
.grid{{position:absolute;inset:0;background-image:linear-gradient(rgba(201,163,91,.05) 1px,transparent 1px),linear-gradient(90deg,rgba(201,163,91,.05) 1px,transparent 1px);background-size:60px 60px;z-index:1;pointer-events:none}}
.panel{{position:absolute;left:{MAPW}px;top:0;width:{W-MAPW}px;height:{H}px;background:var(--panel);border-left:4px solid var(--copper);padding:54px 64px 44px 60px;display:flex;flex-direction:column}}
.corner{{position:absolute;width:26px;height:26px;border-color:var(--brass);border-style:solid;opacity:.7}}
.c1{{top:18px;right:18px;border-width:1px 1px 0 0}} .c2{{bottom:18px;right:18px;border-width:0 1px 1px 0}}
.kicker{{font-size:13px;letter-spacing:.32em;color:var(--copper);text-transform:uppercase;display:flex;gap:14px;align-items:center}}
.kicker b{{font-weight:500;color:var(--brass)}} .kicker .dot{{width:5px;height:5px;background:var(--copper);transform:rotate(45deg)}}
h1{{font-family:'Cormorant Garamond',serif;font-weight:500;font-size:{spec.get('headline_size',50)}px;line-height:1.08;margin:22px 0 14px;color:var(--bone)}}
.dek{{font-family:'Cormorant Garamond',serif;font-style:italic;font-size:23px;line-height:1.3;color:#cdbfa8}}
.meta{{display:flex;align-items:center;gap:18px;margin-top:20px;font-size:14px;color:var(--bone);font-weight:500}}
.bars{{display:flex;gap:5px}} .bars i{{width:10px;height:15px;border:1.5px solid var(--copper)}} .bars i.on{{background:var(--copper)}}
.deco{{margin:26px 0 22px;height:9px;position:relative}}
.deco:before,.deco:after{{content:"";position:absolute;left:0;right:0;height:1px;background:var(--rule)}} .deco:before{{top:0}} .deco:after{{bottom:0}}
.deco span{{position:absolute;left:50%;top:50%;width:9px;height:9px;margin:-4.5px;border:1px solid var(--brass);transform:rotate(45deg);background:var(--panel)}}
.label{{font-size:12px;letter-spacing:.3em;color:var(--copper-dim);text-transform:uppercase;margin-bottom:10px}}
.brief{{font-family:'Cormorant Garamond',serif;font-size:21px;line-height:1.38;color:var(--bone);margin-bottom:22px}}
ul{{list-style:none;margin-bottom:20px}} li{{font-size:14px;line-height:1.5;color:#c8bfb1;padding-left:22px;position:relative;margin-bottom:7px}}
li:before{{content:"";position:absolute;left:2px;top:8px;width:6px;height:6px;border:1px solid var(--copper);transform:rotate(45deg)}}
.framing{{display:grid;grid-template-columns:1fr 1fr;gap:22px;margin-bottom:22px}}
.fr{{border-top:1px solid var(--copper-dim);padding-top:10px;position:relative}}
.fr:before{{content:"";position:absolute;top:-4px;left:0;width:7px;height:7px;background:var(--panel);border:1px solid var(--brass);transform:rotate(45deg)}}
.fr .label{{margin:4px 0 6px}} .fr p{{font-family:'Cormorant Garamond',serif;font-size:18px;line-height:1.3;color:#d8cebd}}
.reading{{border-left:2px solid var(--brass);padding:2px 0 2px 16px;margin:-4px 0 22px}}
.reading .label{{margin-bottom:6px;color:var(--brass)}} .reading p{{font-family:'Cormorant Garamond',serif;font-style:italic;font-size:18.5px;line-height:1.3;color:#e2d6c2}}
.foot{{margin-top:auto;display:flex;justify-content:space-between;align-items:flex-end;border-top:1px solid var(--rule);padding-top:16px}}
.srcs{{display:flex;flex-wrap:wrap;gap:6px 18px;font-size:13px;color:var(--ash)}} .srcs span:before{{content:"↗ ";color:var(--copper-dim)}}
.mark{{text-align:right;white-space:nowrap;flex-shrink:0;margin-left:24px;font-size:12px;letter-spacing:.24em;color:var(--copper)}} .mark small{{display:block;color:var(--ash);letter-spacing:.14em;margin-top:4px;font-size:11px}}
</style></head><body>
<div class="map" id="map"><img id="m" src="data:image/png;base64,{map_b64}"><div class="grid"></div>{CAPTION}</div>
<div class="panel"><div class="corner c1"></div><div class="corner c2"></div>
<div class="kicker"><b>{e(spec.get('desk','ΛRX INTERCEPT'))}</b><span class="dot"></span><span>{e(spec.get('category',''))}</span></div>
<h1>{e(spec['headline'])}</h1>
{f'<div class="dek">{e(spec["dek"])}</div>' if spec.get('dek') else ''}
<div class="meta"><span>{e(spec.get('location',''))}</span><span style="color:var(--copper-dim)">·</span><span>{e(spec.get('date',''))}</span>{BARS}</div>
<div class="deco"><span></span></div>
<div class="label">{LB}</div><div class="brief">{e(spec.get('brief',''))}</div>
{framing}
{READING}
{f'<div class="label">{LC}</div><ul>{ctx}</ul>' if ctx else ''}
<div class="foot"><div><div class="label" style="margin-bottom:8px">{LS}</div><div class="srcs">{srcs}</div></div>
<div class="mark">{MARK}<small>{e(spec.get('stamp',''))}</small></div></div>
</div>
<script>
const MW={mw},MH={mh},BW={MAPW},BH={H},pin={json.dumps(pin)};
const s=Math.max(BW/MW,BH/MH)*{zoom}, iw=MW*s, ih=MH*s;
let fx=pin?pin[0]*s:iw/2, fy=pin?pin[1]*s:ih/2;
let ox=Math.min(0,Math.max(BW-iw,BW*0.42-fx)), oy=Math.min(0,Math.max(BH-ih,BH*0.45-fy));
const m=document.getElementById('m'); m.style.width=iw+'px'; m.style.height=ih+'px'; m.style.left=ox+"px"; m.style.top=oy+"px";
const map=document.getElementById('map');
if(pin && {RING}){{const x=fx+ox,y=fy+oy; map.style.setProperty('--fx',x+'px'); map.style.setProperty('--fy',y+'px');
 const r=document.createElement('div'); r.className='ring'; r.style.left=x+'px'; r.style.top=y+'px'; map.appendChild(r);
 const dir = x>BW*0.6?-1:1;
 const t=document.createElement('div'); t.className='tick'; t.style.top=y+'px'; t.style.left=(dir>0?x+46:x-166)+'px'; map.appendChild(t);
 const g=document.createElement('div'); g.className='tag'; g.textContent={json.dumps(spec.get('pin_label') or spec.get('location','').split(',')[0])};
 g.style.top=(y-16)+'px'; map.appendChild(g); g.style.left=(dir>0?x+170:x-170-g.offsetWidth)+'px';}}
else if(pin){{map.style.setProperty('--fx',(fx+ox)+'px'); map.style.setProperty('--fy',(fy+oy)+'px');}}
else {{map.style.setProperty('--fx','50%'); map.style.setProperty('--fy','50%');}}
</script></body></html>"""
    html_path = out.with_suffix(".html")
    html_path.write_text(page)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=spec.get("scale", 2))
        pg.on("pageerror", lambda err: print("JS error:", err, file=sys.stderr))
        pg.goto(html_path.as_uri())
        pg.wait_for_timeout(400)
        overflow = pg.evaluate("document.querySelector('.panel').scrollHeight > document.querySelector('.panel').clientHeight")
        pg.screenshot(path=str(out))
        b.close()
    if not spec.get("keep_html"): html_path.unlink()
    print(f"wrote {out} (crop_x={crop_x}, map {mw}x{mh})" + ("  WARNING: panel text overflows — shorten brief/context or lower headline_size" if overflow else ""))

if __name__ == "__main__":
    main()
