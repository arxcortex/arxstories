#!/usr/bin/env python3
"""Arx trading-card renderer: full-bleed art in a copper Deco frame, title over the art,
three icon panels along the bottom. Every word on the card comes from the spec, so the
text is always exactly what was fact-checked.

Usage: python3 tools/render_card.py spec.json out.png

spec keys:
  art            path to the image (relative to the spec file)
  desk           e.g. "ΛRX ATLAS" or "ΛRX INTERCEPT"
  meta           right side of the top strip, e.g. "1962 AD · ROME"
  title          large title over the art
  title_size     px at 1600-wide (default 76)
  dek            italic line under the title
  body           optional paragraph under the dek
  panels         list of up to 3 {icon, label, text}
  focus          [x, y] in art pixels to keep in frame (default centre)
  zoom           default 1.0
  grade          "warm" (default), "copper", "mono", "none"
  caption        small plate line on the art, e.g. "Illustration"
  scale          device pixel ratio (default 2 -> 3200x1800)
Icons: laurel, swords, temple, map, keys, scroll, globe, dove, crown, crossed-keys, book,
       scales, flame, anchor, tower, eye
"""
import base64, html, json, sys
from pathlib import Path
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render import ensure_fonts, font_css  # same fonts as the map card

S = 'fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"'
ICONS = {
    "laurel": f'<svg viewBox="0 0 64 64" {S}><path d="M32 54c-10-4-18-14-18-28"/><path d="M32 54c10-4 18-14 18-28"/>' + "".join(
        f'<ellipse cx="{x}" cy="{y}" rx="3.2" ry="6" transform="rotate({r} {x} {y})"/>' for x, y, r in
        [(16, 22, -20), (17, 31, -40), (21, 40, -55), (26, 47, -70), (48, 22, 20), (47, 31, 40), (43, 40, 55), (38, 47, 70)]) + '</svg>',
    "swords": f'<svg viewBox="0 0 64 64" {S}><path d="M14 14l28 28M50 14L22 42"/><path d="M38 46l8-8M18 38l8 8"/><path d="M14 14l-2-6 6 2M50 14l2-6-6 2"/><path d="M44 48l4 4M20 48l-4 4"/></svg>',
    "temple": f'<svg viewBox="0 0 64 64" {S}><path d="M10 24L32 12l22 12H10z"/><path d="M14 28v20M24 28v20M34 28v20M44 28v20M50 28v20"/><path d="M10 52h44M12 48h40"/></svg>',
    "map": f'<svg viewBox="0 0 64 64" {S}><path d="M10 16l14-5 16 5 14-5v37l-14 5-16-5-14 5z"/><path d="M24 11v37M40 16v37"/><path d="M30 28l4 6 6-10" /></svg>',
    "keys": f'<svg viewBox="0 0 64 64" {S}><circle cx="20" cy="20" r="7"/><circle cx="44" cy="20" r="7"/><path d="M25 25l22 26M39 25L17 51"/><path d="M42 46l4-3M45 50l4-3M22 46l-4-3M19 50l-4-3"/></svg>',
    "scroll": f'<svg viewBox="0 0 64 64" {S}><path d="M18 12h28a6 6 0 0 1 0 12H18"/><path d="M18 12a6 6 0 0 0 0 12v28a6 6 0 0 0 6 0h22"/><path d="M46 24v24a6 6 0 0 1-6 6"/><path d="M26 32h14M26 40h14"/></svg>',
    "globe": f'<svg viewBox="0 0 64 64" {S}><circle cx="32" cy="32" r="20"/><path d="M12 32h40M32 12c-7 6-7 34 0 40M32 12c7 6 7 34 0 40"/><path d="M16 22h32M16 42h32"/></svg>',
    "dove": f'<svg viewBox="0 0 64 64" {S}><path d="M12 36c8 0 14-4 18-12 2 8 8 12 16 12-4 6-10 10-18 10-6 0-11-3-16-10z"/><path d="M30 24c-2-6 2-12 8-12 0 6-2 10-8 12z"/><path d="M46 36l8-2"/></svg>',
    "crown": f'<svg viewBox="0 0 64 64" {S}><path d="M12 44l-2-22 12 10 10-16 10 16 12-10-2 22z"/><path d="M12 50h40"/></svg>',
    "book": f'<svg viewBox="0 0 64 64" {S}><path d="M32 18c-6-4-14-5-20-4v34c6-1 14 0 20 4 6-4 14-5 20-4V14c-6-1-14 0-20 4z"/><path d="M32 18v34"/></svg>',
    "scales": f'<svg viewBox="0 0 64 64" {S}><path d="M32 12v40M20 52h24M14 20h36"/><path d="M14 20l-6 14h12zM50 20l-6 14h12z"/></svg>',
    "flame": f'<svg viewBox="0 0 64 64" {S}><path d="M32 54c-10 0-16-7-16-16 0-10 10-14 10-26 8 6 10 12 10 16 3-2 4-6 4-8 5 5 8 11 8 18 0 9-6 16-16 16z"/></svg>',
    "anchor": f'<svg viewBox="0 0 64 64" {S}><circle cx="32" cy="14" r="5"/><path d="M32 19v35M22 28h20"/><path d="M12 40c2 8 10 14 20 14s18-6 20-14"/></svg>',
    "tower": f'<svg viewBox="0 0 64 64" {S}><path d="M22 54V22h20v32M18 54h28M22 22l-2-8h6v4h4v-4h4v4h4v-4h6l-2 8"/><path d="M30 54v-8a2 2 0 0 1 4 0v8"/></svg>',
    "eye": f'<svg viewBox="0 0 64 64" {S}><path d="M8 32c6-10 14-16 24-16s18 6 24 16c-6 10-14 16-24 16S14 42 8 32z"/><circle cx="32" cy="32" r="7"/></svg>',
}
ICONS["crossed-keys"] = ICONS["keys"]

GRADES = {
    "warm": "saturate(1.06) contrast(1.03)",   # keeps the art's own color
    "natural": "none",
    "copper": "grayscale(1) sepia(.75) saturate(1.6) hue-rotate(-12deg) contrast(1.12) brightness(.78)",
    "mono": "grayscale(1) contrast(1.15) brightness(.8)",
    "none": "none",
}


def main():
    spec_path = Path(sys.argv[1]).resolve()
    spec = json.loads(spec_path.read_text())
    out = Path(sys.argv[2]).resolve()
    art = Path(spec["art"])
    if not art.is_absolute():
        art = spec_path.parent / art
    img = Image.open(art).convert("RGB")
    aw, ah = img.size
    tmp = out.parent / (out.stem + ".art.jpg")
    img.save(tmp, quality=92)
    art_b64 = base64.b64encode(tmp.read_bytes()).decode()
    tmp.unlink()

    ensure_fonts()
    e = lambda s: html.escape(str(s or ""))
    W, H = 1600, 900
    ART_TOP, ART_BOTTOM = 70, 724          # art window inside the frame
    focus = spec.get("focus") or [aw / 2, ah / 2]
    zoom = float(spec.get("zoom", 1.0))
    grade = GRADES.get(spec.get("grade", "warm"), GRADES["warm"])
    panels = spec.get("panels", [])[:3]
    panel_html = "".join(
        f'<div class="pn"><div class="ic">{ICONS.get(p.get("icon", "laurel"), ICONS["laurel"])}</div>'
        f'<div><div class="pl">{e(p.get("label"))}</div><div class="pt">{e(p.get("text"))}</div></div></div>'
        for p in panels)
    body = f'<div class="body">{e(spec["body"])}</div>' if spec.get("body") else ""
    cap = f'<div class="cap">{e(spec["caption"])}</div>' if spec.get("caption") else ""

    page = f"""<!doctype html><html><head><meta charset="utf-8"><style>
{font_css()}
:root{{--ink:#0b0a09;--copper:#d4875a;--dim:#8a5a3c;--brass:#c9a35b;--bone:#ece4d6;--ash:#9a9286;}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{width:{W}px;height:{H}px;background:var(--ink);overflow:hidden;position:relative;color:var(--bone)}}
.frame{{position:absolute;inset:10px;border:2px solid var(--brass);outline:1px solid var(--dim);outline-offset:4px}}
.key{{position:absolute;width:26px;height:26px;border:2px solid var(--brass);background:var(--ink)}}
.key:after{{content:"";position:absolute;inset:5px;border:2px solid var(--copper)}}
.k1{{top:2px;left:2px}} .k2{{top:2px;right:2px}} .k3{{bottom:2px;left:2px}} .k4{{bottom:2px;right:2px}}
.strip{{position:absolute;left:62px;right:62px;top:14px;height:52px;display:flex;align-items:center;gap:26px}}
.desk{{font-family:'Cormorant Garamond',serif;font-weight:600;font-size:42px;letter-spacing:.16em;color:var(--brass);white-space:nowrap}}
.rule{{flex:1;height:1px;background:linear-gradient(90deg,var(--brass),rgba(201,163,91,.15))}}
.meta{{font-family:'Cormorant Garamond',serif;font-size:21px;letter-spacing:.2em;text-transform:uppercase;color:var(--bone);white-space:nowrap}}
.art{{position:absolute;left:14px;right:14px;top:{ART_TOP}px;height:{ART_BOTTOM-ART_TOP}px;overflow:hidden;border-top:1px solid var(--brass);border-bottom:2px solid var(--brass)}}
.art img{{position:absolute;filter:{grade}}}
.art:after{{content:"";position:absolute;inset:0;background:
  linear-gradient(0deg,rgba(11,10,9,.94) 0%,rgba(11,10,9,.6) 22%,rgba(11,10,9,0) 44%),
  linear-gradient(90deg,rgba(11,10,9,.32) 0%,rgba(11,10,9,0) 38%)}}
.cap{{position:absolute;right:22px;top:16px;z-index:3;font-family:'JetBrains Mono',monospace;font-size:11px;letter-spacing:.24em;text-transform:uppercase;color:var(--brass);background:rgba(11,10,9,.7);padding:6px 10px;border-right:2px solid var(--copper)}}
.titles{{position:absolute;left:52px;right:52px;bottom:{H-ART_BOTTOM+20}px;z-index:2}}
h1{{font-family:'Cormorant Garamond',serif;font-weight:600;font-size:{spec.get('title_size',76)}px;line-height:.98;color:#f3ead9;text-shadow:0 2px 18px rgba(0,0,0,.85),0 0 4px rgba(0,0,0,.6);max-width:1100px}}
.dek{{font-family:'Cormorant Garamond',serif;font-style:italic;font-size:30px;color:var(--copper);margin-top:8px;text-shadow:0 2px 12px rgba(0,0,0,.7)}}
.body{{font-family:'Cormorant Garamond',serif;font-size:21px;line-height:1.35;color:var(--bone);margin-top:12px;max-width:1420px;text-shadow:0 1px 8px rgba(0,0,0,.8)}}
.band{{position:absolute;left:40px;right:40px;top:{ART_BOTTOM+14}px;bottom:30px;display:grid;grid-template-columns:repeat({max(1, len(panels))},1fr)}}
.pn{{display:flex;gap:20px;align-items:center;padding:0 26px;border-left:1px solid var(--dim)}}
.pn:first-child{{border-left:none;padding-left:8px}}
.ic{{flex:0 0 92px;height:92px;border:2px solid var(--copper);border-radius:50%;display:flex;align-items:center;justify-content:center;color:var(--brass)}}
.ic svg{{width:54px;height:54px}}
.pl{{font-family:'Cormorant Garamond',serif;font-weight:600;font-size:19px;letter-spacing:.14em;text-transform:uppercase;color:var(--copper);margin-bottom:5px}}
.pt{{font-family:'Cormorant Garamond',serif;font-size:18.5px;line-height:1.28;color:var(--bone)}}
</style></head><body>
<div class="art" id="art"><img id="m" src="data:image/jpeg;base64,{art_b64}">{cap}</div>
<div class="titles"><h1>{e(spec['title'])}</h1>{f'<div class="dek">{e(spec["dek"])}</div>' if spec.get('dek') else ''}{body}</div>
<div class="frame"><div class="key k1"></div><div class="key k2"></div><div class="key k3"></div><div class="key k4"></div></div>
<div class="strip"><div class="desk">{e(spec.get('desk','ΛRX ATLAS'))}</div><div class="rule"></div><div class="meta">{e(spec.get('meta',''))}</div></div>
<div class="band">{panel_html}</div>
<script>
const AW={aw},AH={ah},BW={W-28},BH={ART_BOTTOM-ART_TOP},f={json.dumps(focus)};
const s=Math.max(BW/AW,BH/AH)*{zoom}, iw=AW*s, ih=AH*s;
const ox=Math.min(0,Math.max(BW-iw,BW/2-f[0]*s)), oy=Math.min(0,Math.max(BH-ih,BH*0.42-f[1]*s));
const m=document.getElementById('m'); m.style.width=iw+'px'; m.style.height=ih+'px'; m.style.left=ox+'px'; m.style.top=oy+'px';
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
        over = pg.evaluate("""() => { const t=document.querySelector('.titles').getBoundingClientRect();
            const bad=[...document.querySelectorAll('.pn')].some(p=>p.scrollHeight>p.clientHeight+2);
            return t.top < 80 || bad; }""")
        pg.screenshot(path=str(out))
        b.close()
    if not spec.get("keep_html"):
        html_path.unlink()
    print(f"wrote {out} (art {aw}x{ah})" + ("  WARNING: text overflows; shorten body/panels or lower title_size" if over else ""))


if __name__ == "__main__":
    main()
