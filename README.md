# Arx Stories — ΛRX Intercept & ΛRX Atlas

Two map-driven desks for [arxcortex.io](https://arxcortex.io), built the same way:

- **ΛRX Intercept** (`dispatches/`): current news. Neutral, attributed, cold-voiced. Left Framing / Right Framing plus The Stakes.
- **ΛRX Atlas** (`atlas/`): historical events. A narrative, Herodotus-style inquiry that tells the story the way its people told it, then weighs that against the evidence. "As the Romans Tell It" / "As the Evidence Allows".

Each entry takes one item from the Arx map, researches it, and publishes two things:

- **A dispatch card** — the map, zoomed on the story's location, with a neutral headline, a brief, a Left Framing / Right Framing pair, dated context and sources, in the Arx copper/Deco style.
- **A short article** — 300–400 words, with every argument credited to whoever makes it, and the sources listed underneath.

## Layout

```
dispatches/
  YYYY-MM-DD-short-slug/
    index.md      article: YAML front matter (metadata) + Markdown body
    card.png      the rendered dispatch card (3200×1800)
    source.jpg    the original screenshot from the site map
    spec.json     the input used to render card.png (re-render any time)
atlas/
  <year>-short-slug/  same four files; e.g. 509bc-founding-of-the-roman-republic
data/
  dispatches.json generated Intercept manifest, newest first
  atlas.json      generated Atlas manifest, earliest year first
tools/
  render.py       spec.json → card.png (map + side panel layout)
  render_card.py  spec.json → card.png (trading-card layout: art in a Deco frame, title, three icon panels)
  build_index.py  front matter → data/dispatches.json and data/atlas.json
```

## Wiring it into the site (later)

The site needs only `data/dispatches.json` and `data/atlas.json` (each is `{desk, count, entries[]}`). Every entry carries its metadata plus repo-relative `path` (the article Markdown) and `card` (the PNG), so a page can list dispatches, show cards, drop pins on a map with `coords`, and render the article from Markdown. Nothing in this repo assumes a particular site build. Serve it from GitHub raw, a Netlify build step, or a git submodule.

## Front matter fields

| field | notes |
|---|---|
| `slug` | must equal the folder name |
| `desk`, `author` | `ΛRX Intercept`, the desk persona |
| `category` | category from the site map (Conflict, …) |
| `title`, `dek` | neutral headline and one-line summary, claims attributed |
| `date` | `YYYY-MM-DD` |
| `location`, `coords` | display location; `[lat, lon]` for map pins |
| `severity` | 0–5, from the site map |
| `card` | card filename in the folder (the shareable card; used for X previews and the click-to-view dialog) |
| `art` | the clean art with no card text (`art.jpg`); story pages and the site lead with it |
| `framing.left`, `framing.right` | one attributed sentence each |
| `reading.label`, `reading.text` | The Stakes: one sentence, same weight for every side |
| `tags` | lowercase, hyphenated |
| `sources` | list of `{title, outlet, url, role}`; role is `origin`, `context`, `framing-left`, `framing-right` or `image` |

Atlas entries add `kind: atlas`, `year` (negative for BC, used for sorting), a display `date` such as `509 BC`, a `pair` block with custom labels instead of `framing`, and `witnesses` (the ancient or primary sources). Their `sources` roles are `primary` or `scholarship`.

## Adding a dispatch

```bash
pip install -r tools/requirements.txt    # Pillow, Playwright, PyYAML (and: playwright install chromium)
mkdir dispatches/2026-10-26-some-slug
# add source.jpg, spec.json, index.md
python3 tools/render.py dispatches/2026-10-26-some-slug/spec.json dispatches/2026-10-26-some-slug/card.png
python3 tools/build_index.py
git add -A && git commit -m "Dispatch: <title>"
```

Card image options in `spec.json`: `map_box` (crop), `pin` + `ring` (focus point, with or without the copper ring), `zoom` (default 1.05), `grade` (`ink` default, `copper`, `mono`, `none`), `caption` (a plate line over the image), `labels` (rename any card section), `mark`. Any image works: map screenshots, photos, paintings, documents, charts.

Fonts (Cormorant Garamond, JetBrains Mono) are fetched once with `npm pack` into `tools/fonts/` (git-ignored).

## Editorial standard

**Atlas:** the voice may narrate, linger and tell the story with the color its tellers gave it, in the manner of Herodotus: "the Romans say", "so they tell it", "whether it happened so, I cannot say". Legend is always marked as what the sources say, and a separate passage weighs it against what historians and evidence allow. Nothing is invented; every detail traces to an ancient witness or a modern scholar.

**Intercept:**

Stories needn't be political. Each Intercept entry has a `story_type`: `partisan` (Left Framing / Right Framing + The Stakes), `contested` (the actual sides by name, e.g. "The Company Says / Regulators Say", + The Stakes) or `uncontested` (What's Known / What's Still Open + Why It Matters, or neither).

The desk reads politics with a realist eye: public appeals are the formal language, and The Stakes names the concrete thing beneath them (who gains or keeps control of which office, rule, institution or resource). It applies to every side alike and describes stakes and incentives; it never asserts private motives as fact.

The card and article state only checkable facts in their own voice. Every interpretation or argument is credited, in active voice, to a named person, outlet, party or group, and the same verb is used for both sides. Before publishing, apply the flip test: would a reader on the left and a reader on the right each find the headline, dek, brief and context fair?
