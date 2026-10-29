#!/usr/bin/env python3
"""Rebuild the site manifests from front matter.

  dispatches/*/index.md -> data/dispatches.json  (ΛRX Intercept, newest first)
  atlas/*/index.md      -> data/atlas.json       (ΛRX Atlas, earliest year first)
  currents/*/index.md   -> data/currents.json    (ΛRX Currents, newest first)

Usage: python3 tools/build_index.py   (from anywhere)

Paths in the manifests are repo-relative so the site can resolve them against
wherever the repo is served from.
"""
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent

COLLECTIONS = {
    "dispatches": {
        "desk": "ΛRX Intercept",
        "out": "data/dispatches.json",
        "required": ["slug", "title", "dek", "date", "location", "category", "card", "sources"],
        "sort": lambda m: str(m["date"]),
        "reverse": True,
    },
    "atlas": {
        "desk": "ΛRX Atlas",
        "out": "data/atlas.json",
        "required": ["slug", "title", "dek", "date", "year", "location", "category", "card", "sources"],
        "sort": lambda m: int(m["year"]),
        "reverse": False,
    },
    "currents": {
        "desk": "ΛRX Currents",
        "out": "data/currents.json",
        "required": ["slug", "title", "dek", "date", "location", "category", "card", "sources"],
        "sort": lambda m: str(m["date"]),
        "reverse": True,
    },
}


def parse(md_path, required):
    text = md_path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise ValueError(f"{md_path}: missing front matter")
    _, fm, body = text.split("---", 2)
    meta = yaml.safe_load(fm)
    missing = [k for k in required if meta.get(k) in (None, "", [])]
    if missing:
        raise ValueError(f"{md_path}: missing {missing}")
    if meta["slug"] != md_path.parent.name:
        raise ValueError(f"{md_path}: slug '{meta['slug']}' must match folder name '{md_path.parent.name}'")
    folder = md_path.parent.relative_to(ROOT).as_posix()
    meta["date"] = str(meta["date"])
    meta["path"] = f"{folder}/index.md"
    meta["card"] = f"{folder}/{meta['card']}"
    if meta.get("art"):
        if not (md_path.parent / meta["art"]).is_file():
            raise ValueError(f"{md_path}: art file '{meta['art']}' not found")
        meta["art"] = f"{folder}/{meta['art']}"
    if "series" in meta:
        series = meta["series"]
        if isinstance(series, str):
            series = [series]
        bad = [x for x in series or [] if x not in COLLECTIONS and x != "dispatch"]
        if not isinstance(series, list) or bad:
            raise ValueError(f"{md_path}: series must be a list drawn from {list(COLLECTIONS)}, got {meta['series']!r}")
        meta["series"] = series
    if "memeplex" in meta and not isinstance(meta["memeplex"], dict):
        raise ValueError(f"{md_path}: memeplex must be a mapping with 'ideas' and optional 'current'")
    meta["words"] = len(body.split())
    return meta


def main():
    errors = []
    for folder, cfg in COLLECTIONS.items():
        entries = []
        for md in sorted((ROOT / folder).glob("*/index.md")) if (ROOT / folder).is_dir() else []:
            try:
                entries.append(parse(md, cfg["required"]))
            except Exception as e:  # report every problem, not just the first
                errors.append(str(e))
        entries.sort(key=cfg["sort"], reverse=cfg["reverse"])
        out = ROOT / cfg["out"]
        out.parent.mkdir(exist_ok=True)
        out.write_text(json.dumps({"desk": cfg["desk"], "count": len(entries), "entries": entries},
                                  ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {cfg['out']} ({len(entries)} entries)")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
