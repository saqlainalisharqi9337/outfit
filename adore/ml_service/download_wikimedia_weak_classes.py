"""Download CC-licensed Wikimedia Commons images for weak Adore classes.

Uses only the public Commons API (CC0 / CC-BY / CC-BY-SA / Public Domain).
No commercial site scraping.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

DST_DEFAULT = Path(r"D:\fyp project\dataset")
UA = "AdoreFYP/1.0 (educational; contact: local-dev)"

QUERIES: list[tuple[str, str, str]] = [
    ("handbag", "accessories", "bag"),
    ("tote bag", "accessories", "bag"),
    ("backpack", "accessories", "bag"),
    ("sun hat", "accessories", "hat"),
    ("baseball cap", "accessories", "hat"),
    ("beanie hat", "accessories", "hat"),
    ("high heels shoes", "footwear", "heels"),
    ("stiletto heels", "footwear", "heels"),
    ("pencil skirt", "bottomwear", "skirt"),
    ("pleated skirt", "bottomwear", "skirt"),
    ("evening dress", "one-piece", "dress"),
]

ALLOWED_LICENSES = {
    "cc-zero",
    "cc0",
    "cc-by-4.0",
    "cc-by-3.0",
    "cc-by-2.0",
    "cc-by-sa-4.0",
    "cc-by-sa-3.0",
    "cc-by-sa-2.0",
}


def _api(params: dict) -> dict:
    q = urllib.parse.urlencode({**params, "format": "json"})
    url = f"https://commons.wikimedia.org/w/api.php?{q}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            time.sleep(0.8 * (attempt + 1))
    raise last_exc or RuntimeError("commons API failed")


def search_files(query: str, limit: int = 50) -> list[str]:
    data = _api(
        {
            "action": "query",
            "list": "search",
            "srsearch": f"filetype:bitmap {query}",
            "srnamespace": "6",
            "srlimit": str(min(limit, 50)),
        }
    )
    return [hit["title"] for hit in data.get("query", {}).get("search", [])]


def file_info(titles: list[str]) -> list[dict]:
    if not titles:
        return []
    data = _api(
        {
            "action": "query",
            "titles": "|".join(titles[:40]),
            "prop": "imageinfo",
            "iiprop": "url|size|mime|extmetadata",
            "iiurlwidth": "800",
        }
    )
    out = []
    for page in data.get("query", {}).get("pages", {}).values():
        infos = page.get("imageinfo") or []
        if not infos:
            continue
        info = infos[0]
        meta = info.get("extmetadata") or {}
        license_short = (
            (meta.get("LicenseShortName") or {}).get("value")
            or (meta.get("License") or {}).get("value")
            or ""
        ).lower().replace(" ", "")
        license_name = ((meta.get("License") or {}).get("value") or "").lower()
        ok = any(lic in license_short for lic in ALLOWED_LICENSES)
        if not ok:
            if (
                "publicdomain" not in license_short
                and "pd-" not in license_short
                and "public domain" not in license_name
                and "cc0" not in license_name
            ):
                continue
        url = info.get("thumburl") or info.get("url")
        if not url:
            continue
        mime = (info.get("mime") or "").lower()
        if "jpeg" not in mime and "png" not in mime and "webp" not in mime:
            continue
        if (info.get("size") or 0) < 8_000:
            continue
        out.append({"url": url, "title": page.get("title", ""), "license": license_short})
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dst", type=Path, default=DST_DEFAULT)
    ap.add_argument("--per-query", type=int, default=35)
    ap.add_argument("--prefix", default="wiki_")
    args = ap.parse_args()

    copied = 0
    counts: Counter[str] = Counter()
    seen: set[str] = set()

    for query, family, leaf in QUERIES:
        print(f"search: {query} -> {family}/{leaf}")
        try:
            titles = search_files(query, limit=args.per_query)
            infos = file_info(titles)
        except Exception as exc:  # noqa: BLE001
            print(f"  skip query ({exc})")
            continue
        for info in infos:
            try:
                req = urllib.request.Request(info["url"], headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=60) as resp:
                    raw = resp.read()
            except Exception as exc:  # noqa: BLE001
                print("  skip", exc)
                continue
            if len(raw) < 5_000:
                continue
            digest = hashlib.sha1(raw).hexdigest()[:16]
            if digest in seen:
                continue
            seen.add(digest)
            h = int(digest[:8], 16)
            split = "test" if h % 10 == 0 else ("val" if h % 10 == 1 else "train")
            ext = ".png" if "png" in info["url"].lower() else ".jpg"
            dest_dir = args.dst / split / split / family / leaf
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / f"{args.prefix}{leaf}_{digest}{ext}"
            if dest.exists():
                continue
            dest.write_bytes(raw)
            copied += 1
            counts[f"{family}/{leaf}"] += 1
            time.sleep(0.12)
        print(f"  kept: {dict(counts)}")
        time.sleep(0.35)

    print("done copied", copied, dict(counts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
