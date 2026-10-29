#!/usr/bin/env python3
"""Build the public story pages into _site/.

Reads the manifests that tools/build_index.py writes. Does not edit article
markdown, cards, spec.json, or fact-checks. The committed manifests stay as
they are. URL fields are added only on the copies published to GitHub Pages.

  python tools/build_site.py
"""
import html
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "_site"
PAGES = "https://arxcortex.github.io/arxstories"
PRETTY = "https://arxcortex.io"

COLLECTIONS = (
    ("data/dispatches.json", "dispatches", "intercept"),
    ("data/atlas.json", "atlas", "atlas"),
    ("data/currents.json", "currents", "currents"),
)

MEMEPLEX = "https://arxcortex.io/memeplex.html"
SERIES_LABELS = {"dispatches": "ΛRX Intercept", "dispatch": "ΛRX Intercept", "atlas": "ΛRX Atlas", "currents": "ΛRX Currents"}

IMG_LINE = re.compile(r"^!\[([^\]]*)\]\(([^)]+)\)\s*$")
IMG_INLINE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
BOLD = re.compile(r"\*\*([^*]+)\*\*")
ITALIC = re.compile(r"\*([^*]+)\*")


def escape(text):
    return html.escape(text or "", quote=True)


def abs_url(src, base):
    if src.startswith(("http://", "https://")):
        return src
    return base + src.lstrip("./")


def display_url(url):
    if url.endswith("/card.png") or url.endswith("card.png"):
        return url[:-4] + ".webp"
    return url


def inline(text, asset_base):
    text = escape(text)

    def img(match):
        alt = match.group(1)
        src = html.unescape(match.group(2))
        url = display_url(abs_url(src, asset_base))
        return (
            f'<img src="{escape(url)}" alt="{alt}" width="960" height="540" loading="lazy">'
        )

    text = IMG_INLINE.sub(img, text)

    def link(match):
        label = match.group(1)
        url = html.unescape(match.group(2))
        if not url.startswith(("http://", "https://")):
            url = "#"
        return f'<a href="{escape(url)}" rel="noopener" target="_blank">{label}</a>'

    text = LINK.sub(link, text)
    text = BOLD.sub(r"<strong>\1</strong>", text)
    text = ITALIC.sub(r"<em>\1</em>", text)
    return text


def render_body(body, asset_base, hero=None):
    parts = []
    for block in re.split(r"\n\s*\n", body.strip()):
        lines = block.split("\n")
        i = 0
        while i < len(lines):
            line = lines[i].rstrip()
            image = IMG_LINE.match(line)
            if image:
                alt = image.group(1)
                src = image.group(2)
                url = display_url(abs_url(src, asset_base))
                cap_text = "Illustration · " if "illustration" in alt.lower() else ""
                if hero and Path(src).name == hero["card_name"]:
                    parts.append(
                        f'<figure class="plate hero">'
                        f'<a class="cardlink" href="{escape(hero["card_png"])}" data-card="{escape(hero["card_display"])}" '
                        f'aria-label="View the shareable card">'
                        f'<img src="{escape(hero["art_url"])}" alt="{escape(alt)}" width="{hero["w"]}" height="{hero["h"]}">'
                        f'<span class="badge">View card</span></a>'
                        f'<figcaption>{cap_text}<a class="cardlink" href="{escape(hero["card_png"])}" '
                        f'data-card="{escape(hero["card_display"])}">View the shareable card</a></figcaption></figure>'
                    )
                    i += 1
                    continue
                cap = "<figcaption>Illustration</figcaption>" if cap_text else ""
                parts.append(
                    f'<figure class="plate"><img src="{escape(url)}" alt="{escape(alt)}" '
                    f'width="960" height="540" loading="lazy">{cap}</figure>'
                )
            elif line.startswith("### "):
                parts.append(f"<h3>{inline(line[4:], asset_base)}</h3>")
            elif line.startswith("## "):
                parts.append(f"<h2>{inline(line[3:], asset_base)}</h2>")
            elif line.startswith("# "):
                parts.append(f"<h1>{inline(line[2:], asset_base)}</h1>")
            elif line.strip() == "---":
                parts.append("<hr>")
            elif line.startswith("- "):
                items = []
                while i < len(lines) and lines[i].startswith("- "):
                    items.append(f"<li>{inline(lines[i][2:], asset_base)}</li>")
                    i += 1
                parts.append("<ul>" + "".join(items) + "</ul>")
                continue
            elif line.strip():
                html_line = inline(line, asset_base)
                plain = re.sub(r"<[^>]+>", "", html_line)
                if plain.startswith("Claude Opus 5.5 wrote this"):
                    parts.append(f'<p class="colophon">{html_line}</p>')
                else:
                    parts.append(f"<p>{html_line}</p>")
            i += 1
    return "\n".join(parts)


def idea_name(idea_id):
    words = str(idea_id).replace("-", "_").split("_")
    return " ".join(words).capitalize()


def render_links(entry):
    """Series and Memeplex lines from front matter, placed before ## Sources."""
    parts = []
    series = entry.get("series") or []
    if len(series) > 1:
        labels = " × ".join(escape(SERIES_LABELS.get(s, s)) for s in series)
        parts.append(f'<p class="series">Series · {labels}</p>')
    memeplex = entry.get("memeplex") or {}
    ideas = memeplex.get("ideas") or []
    if ideas:
        # memeplex.html has no per-idea deep links yet, so ideas are plain names.
        names = " · ".join(escape(idea_name(i)) for i in ideas)
        parts.append(
            f'<p class="memeplex"><a href="{MEMEPLEX}" rel="noopener" target="_blank">On the Memeplex</a>'
            f' · {names}</p>'
        )
    return "\n".join(parts)


def split_markdown(text):
    if not text.startswith("---"):
        raise ValueError("missing front matter")
    _, fm, body = text.split("---", 2)
    return fm, body


def write_display(src, dest, max_w=960):
    from PIL import Image

    with Image.open(src) as im:
        width, height = im.size
        frame = im.convert("RGBA") if im.mode in ("RGBA", "LA", "P") else im.convert("RGB")
        if width > max_w:
            height_out = max(1, round(height * max_w / width))
            frame = frame.resize((max_w, height_out), Image.Resampling.LANCZOS)
        dest.parent.mkdir(parents=True, exist_ok=True)
        frame.save(dest, "WEBP", quality=82, method=6)
        return width, height, frame.size


PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · {desk}</title>
<meta name="description" content="{dek}">
<link rel="canonical" href="{canonical}">
<meta property="og:type" content="article">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{dek}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{png}">
<meta property="og:image:width" content="{width}">
<meta property="og:image:height" content="{height}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title}">
<meta name="twitter:description" content="{dek}">
<meta name="twitter:image" content="{png}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,500;0,600;1,400;1,500&amp;family=JetBrains+Mono:wght@400;500&amp;display=swap" rel="stylesheet">
<style>
  :root {{ color-scheme: dark; }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; background: #07080c; color: #ede4c8;
    font-family: "Cormorant Garamond", Georgia, serif; font-size: 21px; line-height: 1.55;
  }}
  a {{ color: #e89968; }}
  .wrap {{ max-width: 740px; margin: 0 auto; padding: 32px 22px 80px; }}
  .mast {{
    display: flex; justify-content: space-between; gap: 16px; align-items: baseline;
    font-family: "JetBrains Mono", ui-monospace, monospace; font-size: 11px;
    letter-spacing: 0.18em; text-transform: uppercase; color: #b8ad8e;
  }}
  .mast a {{ color: #e89968; text-decoration: none; }}
  article {{ margin-top: 28px; }}
  h1 {{ font-weight: 500; font-size: 42px; line-height: 1.05; margin: 0.4em 0 0.3em; }}
  h2 {{ font-weight: 500; font-size: 28px; line-height: 1.15; margin: 1.4em 0 0.4em; }}
  p {{ margin: 0 0 0.9em; }}
  .colophon {{
    margin-top: 1.8em; font-size: 13px; line-height: 1.45; font-style: italic; color: #8f866f;
  }}
  strong {{ font-weight: 600; }}
  hr {{ border: 0; border-top: 1px solid rgba(232, 153, 104, 0.35); margin: 1.6em 0; }}
  ul {{ margin: 0 0 1em; padding-left: 1.2em; }}
  .series, .memeplex {{
    font-family: "JetBrains Mono", ui-monospace, monospace; font-size: 12px;
    letter-spacing: 0.08em; color: #b8ad8e; margin: 1.6em 0 0.6em;
  }}
  li {{ margin: 0.25em 0; }}
  .plate {{ margin: 1.2em 0 1.4em; }}
  .plate img {{ width: 100%; height: auto; display: block; border: 1px solid rgba(232, 153, 104, 0.45); }}
  .hero > a.cardlink {{ position: relative; display: block; cursor: zoom-in; }}
  .hero img {{ transition: filter .2s; }}
  .hero > a.cardlink:hover img {{ filter: brightness(1.08); }}
  .badge {{
    position: absolute; right: 10px; bottom: 10px; padding: 6px 10px;
    font-family: "JetBrains Mono", ui-monospace, monospace; font-size: 10px; letter-spacing: .2em;
    text-transform: uppercase; color: #ede4c8; background: rgba(7, 8, 12, .72);
    border: 1px solid rgba(232, 153, 104, .6);
  }}
  dialog.card {{
    padding: 0; border: 1px solid rgba(232, 153, 104, .6); background: #07080c; color: #ede4c8;
    max-width: min(96vw, 1600px); width: 100%;
  }}
  dialog.card::backdrop {{ background: rgba(0, 0, 0, .82); }}
  dialog.card img {{ width: 100%; height: auto; display: block; }}
  dialog.card .bar {{
    display: flex; justify-content: space-between; gap: 12px; padding: 10px 14px;
    font-family: "JetBrains Mono", ui-monospace, monospace; font-size: 11px; letter-spacing: .16em; text-transform: uppercase;
  }}
  dialog.card button {{ all: unset; cursor: pointer; color: #e89968; }}
  figcaption {{
    font-family: "JetBrains Mono", ui-monospace, monospace; font-size: 10px;
    letter-spacing: 0.16em; text-transform: uppercase; color: #b8ad8e; margin-top: 8px;
  }}
  @media (max-width: 640px) {{
    body {{ font-size: 19px; }}
    h1 {{ font-size: 34px; }}
  }}
</style>
</head>
<body>
<div class="wrap">
<header class="mast">
  <a href="https://arxcortex.io/">Arx Cortex</a>
  <span>{desk}</span>
</header>
<article>
{body}
</article>
</div>
<dialog class="card" id="card"><img alt="The shareable ΛRX card" src="" width="1600" height="900">
<div class="bar"><a id="card-dl" href="" download>Download card</a><button type="button" id="card-close">Close</button></div></dialog>
<script>
(function () {{
  var d = document.getElementById("card");
  if (!d || !d.showModal) return;
  var img = d.querySelector("img"), dl = document.getElementById("card-dl");
  document.querySelectorAll("a.cardlink").forEach(function (a) {{
    a.addEventListener("click", function (e) {{
      e.preventDefault();
      img.src = a.dataset.card || a.href;
      dl.href = a.href;
      d.showModal();
    }});
  }});
  document.getElementById("card-close").addEventListener("click", function () {{ d.close(); }});
  d.addEventListener("click", function (e) {{ if (e.target === d) d.close(); }});
}})();
</script>
</body>
</html>
"""


def with_links(body_html, links):
    if not links:
        return body_html
    marker = "<h2>Sources</h2>"
    if marker in body_html:
        return body_html.replace(marker, links + "\n" + marker, 1)
    return body_html + "\n" + links


def build_entry(entry, folder, pretty_desk):
    card = entry.get("card") or ""
    slug = entry.get("slug") or ""
    if not card or not slug:
        raise ValueError(f"missing slug or card for {folder}")
    src_dir = (ROOT / card).parent
    md_path = src_dir / "index.md"
    if not md_path.is_file():
        raise ValueError(f"missing {md_path}")
    _, body = split_markdown(md_path.read_text(encoding="utf-8"))
    asset_base = f"{PAGES}/{folder}/{slug}/"
    canonical = f"{PRETTY}/{pretty_desk}/{slug}/"
    pages_url = f"{PAGES}/{folder}/{slug}/"
    png_name = Path(card).name
    png_src = src_dir / png_name
    if not png_src.is_file():
        raise ValueError(f"missing {png_src}")

    out_dir = SITE / folder / slug
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    for name in ("card.png", "art.png", "source.png", "art.jpg", "source.jpg"):
        src = src_dir / name
        if src.is_file():
            shutil.copy2(src, out_dir / name)

    png_url = asset_base + png_name
    width, height = 1200, 630
    webp_path = out_dir / "card.webp"
    try:
        width, height, _ = write_display(png_src, webp_path, 1600)
    except Exception as exc:
        print(f"webp skipped for {slug}: {exc}", file=sys.stderr)
        if webp_path.exists():
            webp_path.unlink()

    hero = None
    art_rel = entry.get("art") or ""
    art_src = ROOT / art_rel if art_rel else None
    if art_src and art_src.is_file():
        art_webp = out_dir / "art.webp"
        try:
            _, _, (aw, ah) = write_display(art_src, art_webp, 1600)
            hero = {
                "card_name": png_name,
                "card_png": png_url,
                "card_display": asset_base + "card.webp" if webp_path.is_file() else png_url,
                "art_url": asset_base + "art.webp",
                "w": aw, "h": ah,
            }
        except Exception as exc:
            print(f"art webp skipped for {slug}: {exc}", file=sys.stderr)

    page = PAGE.format(
        title=escape(entry.get("title") or slug),
        desk=escape(entry.get("desk") or ""),
        dek=escape(entry.get("dek") or ""),
        canonical=escape(canonical),
        png=escape(png_url),
        width=width,
        height=height,
        body=with_links(render_body(body, asset_base, hero), render_links(entry)),
    )
    (out_dir / "index.html").write_text(page, encoding="utf-8")
    published = dict(entry)
    published["image_url"] = png_url
    published["display_url"] = asset_base + "card.webp" if webp_path.is_file() else png_url
    if hero:
        published["art_url"] = hero["art_url"]
        published["art_image_url"] = asset_base + Path(art_rel).name
    published["page_url"] = canonical
    published["pages_url"] = pages_url
    return published


def write_catalog(published):
    items = []
    current_desk = None
    for entry in published:
        desk = entry.get("desk") or ""
        if desk.upper() == "ΛRX CURRENTS" and desk != current_desk:
            items.append(f'</ul>\n<h2>ΛRX CURRENTS</h2>\n<ul>')
        current_desk = desk
        items.append(
            f'<li><a href="{escape(entry["pages_url"].removeprefix(PAGES + "/"))}">{escape(entry.get("title") or entry["slug"])}</a>'
            f' <span>{escape(entry.get("desk") or "")}</span></li>'
        )
    html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ΛRX Stories</title>
<link rel="canonical" href="{PRETTY}/">
<style>
  body {{ margin: 0; background: #07080c; color: #ede4c8; font-family: Georgia, serif; }}
  main {{ max-width: 680px; margin: 0 auto; padding: 48px 22px; }}
  a {{ color: #e89968; }}
  li {{ margin: 0.6em 0; }}
  span {{ font-family: ui-monospace, monospace; font-size: 12px; letter-spacing: 0.08em; color: #b8ad8e; }}
</style>
</head>
<body>
<main>
<h1>ΛRX Stories</h1>
<ul>
{''.join(items)}
</ul>
</main>
</body>
</html>
"""
    (SITE / "index.html").write_text(html_doc, encoding="utf-8")


def main():
    if SITE.exists():
        shutil.rmtree(SITE)
    SITE.mkdir()
    published = []
    for manifest, folder, pretty_desk in COLLECTIONS:
        path = ROOT / manifest
        if not path.is_file():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        entries = []
        for entry in data.get("entries") or []:
            entries.append(build_entry(entry, folder, pretty_desk))
        data = dict(data)
        data["entries"] = entries
        data["count"] = len(entries)
        out = SITE / manifest
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        published.extend(entries)
        print(f"published {manifest} ({len(entries)})")
    write_catalog(published)
    relative = []
    for page in SITE.rglob("*.html"):
        text = page.read_text(encoding="utf-8")
        for src in re.findall(r'(?:src|href)="([^"]+)"', text):
            if src.startswith(("#", "https://", "http://", "mailto:")):
                continue
            if page.name == "index.html" and page.parent == SITE and not src.startswith(("/", "data:")):
                continue
            relative.append(f"{page.relative_to(SITE)} -> {src}")
    if relative:
        print("\n".join(relative), file=sys.stderr)
        sys.exit(1)
    print(f"wrote {SITE} ({len(published)} pages)")


if __name__ == "__main__":
    main()
