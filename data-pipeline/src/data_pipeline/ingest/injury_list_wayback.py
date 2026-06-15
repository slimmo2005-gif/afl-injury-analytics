"""Historical AFL.com injury list via Wayback Machine and Common Crawl."""

from __future__ import annotations

import json
import time
from datetime import date
from io import BytesIO

import pandas as pd
import requests
from warcio.archiveiterator import ArchiveIterator

from ..config import RAW_DIR, WAYBACK_CDX_CACHE, WAYBACK_INJURY_URL
from .injury_list import parse_injury_list_html

_HEADERS = {"User-Agent": "afl-injury-analytics/0.4"}
_SOURCE = "wayback_afl"
_CC_SOURCE = "commoncrawl_afl"
_CDX_API = "https://web.archive.org/cdx/search/cdx"
_CC_INDEX = "https://index.commoncrawl.org/{crawl}-index"
_CC_DATA = "https://data.commoncrawl.org/{filename}"
_MANIFEST_PATH = RAW_DIR / "wayback_injury_manifest.json"
_CC_INDEX_CACHE = RAW_DIR / "commoncrawl_injury_index.json"
_FETCH_TIMEOUT = 25

_CC_COLLECTIONS_2021 = (
    "CC-MAIN-2021-04",
    "CC-MAIN-2021-10",
    "CC-MAIN-2021-17",
    "CC-MAIN-2021-25",
    "CC-MAIN-2021-31",
    "CC-MAIN-2021-38",
    "CC-MAIN-2021-43",
    "CC-MAIN-2021-49",
)
_CC_COLLECTIONS_2022 = (
    "CC-MAIN-2022-05",
    "CC-MAIN-2022-21",
    "CC-MAIN-2022-27",
    "CC-MAIN-2022-33",
    "CC-MAIN-2022-40",
    "CC-MAIN-2022-49",
)


def _load_cdx_cache() -> list[list[str]]:
    if WAYBACK_CDX_CACHE.exists():
        return json.loads(WAYBACK_CDX_CACHE.read_text(encoding="utf-8"))
    return []


def _save_cdx_cache(rows: list[list[str]]) -> None:
    WAYBACK_CDX_CACHE.parent.mkdir(parents=True, exist_ok=True)
    WAYBACK_CDX_CACHE.write_text(json.dumps(rows), encoding="utf-8")


def discover_wayback_via_available(*, from_year: int, to_year: int) -> list[dict]:
    """Use archive.org/wayback/available when web.archive.org CDX is unreachable."""
    manifest: list[dict] = []
    seen: set[str] = set()
    for year in range(from_year, to_year + 1):
        for month in range(3, 12):
            for day in (1, 15):
                ts = f"{year}{month:02d}{day:02d}"
                try:
                    resp = requests.get(
                        "https://archive.org/wayback/available",
                        params={"url": WAYBACK_INJURY_URL, "timestamp": ts},
                        headers=_HEADERS,
                        timeout=25,
                    )
                    snap = resp.json().get("archived_snapshots", {}).get("closest", {})
                    if snap.get("available") and snap.get("status") == "200":
                        stamp = snap["timestamp"]
                        if stamp not in seen:
                            seen.add(stamp)
                            manifest.append(
                                {"timestamp": stamp, "url": snap["url"], "query": ts}
                            )
                except Exception:
                    pass
                time.sleep(0.2)
    _MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    _MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def query_wayback_cdx(
    *,
    from_year: int,
    to_year: int,
    limit: int = 200,
    use_cache: bool = True,
) -> list[dict]:
    if use_cache:
        cached = _load_cdx_cache()
        if cached and len(cached) > 1:
            return [{"timestamp": r[1], "original": r[2]} for r in cached[1:] if len(r) > 2]

    params = {
        "url": WAYBACK_INJURY_URL.replace("https://", ""),
        "from": f"{from_year}0101",
        "to": f"{to_year}1231",
        "output": "json",
        "filter": "statuscode:200",
        "collapse": "timestamp:6",
        "limit": limit,
    }
    try:
        resp = requests.get(_CDX_API, params=params, headers=_HEADERS, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        if len(data) > 1:
            _save_cdx_cache(data)
        return [{"timestamp": r[1], "original": r[2]} for r in data[1:] if len(r) > 2]
    except Exception as exc:
        print(f"[wayback] CDX query failed: {exc}")
        cached = _load_cdx_cache()
        if cached and len(cached) > 1:
            print("[wayback] using cached CDX index")
            return [{"timestamp": r[1], "original": r[2]} for r in cached[1:] if len(r) > 2]
        print("[wayback] falling back to archive.org/wayback/available discovery")
        return discover_wayback_via_available(from_year=from_year, to_year=to_year)


def fetch_wayback_snapshot(timestamp: str, original_url: str = WAYBACK_INJURY_URL) -> str | None:
    wayback_url = f"https://web.archive.org/web/{timestamp}/{original_url}"
    try:
        resp = requests.get(wayback_url, headers=_HEADERS, timeout=_FETCH_TIMEOUT)
        if resp.status_code == 200 and "PLAYER" in resp.text.upper():
            return resp.text
    except Exception as exc:
        print(f"[wayback] snapshot {timestamp} failed: {exc}")
    return None


def query_common_crawl_index(collections: tuple[str, ...]) -> list[dict]:
    records: list[dict] = []
    seen: set[str] = set()
    for crawl in collections:
        url = _CC_INDEX.format(crawl=crawl)
        try:
            resp = requests.get(
                url,
                params={"url": "afl.com.au/matches/injury-list", "output": "json", "limit": 5},
                headers=_HEADERS,
                timeout=30,
            )
            if resp.status_code != 200 or not resp.text.strip():
                continue
            for line in resp.text.strip().split("\n"):
                rec = json.loads(line)
                if rec.get("status") != "200":
                    continue
                key = rec["timestamp"]
                if key in seen:
                    continue
                seen.add(key)
                rec["crawl"] = crawl
                records.append(rec)
        except Exception as exc:
            print(f"[commoncrawl] index {crawl} failed: {exc}")
    records.sort(key=lambda r: r["timestamp"])
    _CC_INDEX_CACHE.parent.mkdir(parents=True, exist_ok=True)
    _CC_INDEX_CACHE.write_text(json.dumps(records, indent=2), encoding="utf-8")
    return records


def fetch_common_crawl_html(record: dict) -> str | None:
    filename = record["filename"]
    offset = int(record["offset"])
    length = int(record["length"])
    data_url = _CC_DATA.format(filename=filename)
    headers = {"Range": f"bytes={offset}-{offset + length - 1}"}
    try:
        warc_bytes = requests.get(data_url, headers=headers, timeout=90).content
        for warc_record in ArchiveIterator(BytesIO(warc_bytes)):
            if warc_record.rec_type == "response":
                return warc_record.content_stream().read().decode("utf-8", "replace")
    except Exception as exc:
        print(f"[commoncrawl] fetch {record.get('timestamp')} failed: {exc}")
    return None


def fetch_common_crawl_injury_lists(
    *,
    from_year: int = 2021,
    to_year: int = 2022,
    sleep_s: float = 0.5,
) -> pd.DataFrame:
    collections: list[str] = []
    if from_year <= 2021 <= to_year:
        collections.extend(_CC_COLLECTIONS_2021)
    if from_year <= 2022 <= to_year:
        collections.extend(_CC_COLLECTIONS_2022)

    records = query_common_crawl_index(tuple(collections))
    records = [
        r
        for r in records
        if from_year <= int(r["timestamp"][:4]) <= to_year
    ]
    if not records:
        print("[commoncrawl] no captures found")
        return pd.DataFrame()

    frames: list[pd.DataFrame] = []
    for i, rec in enumerate(records):
        html = fetch_common_crawl_html(rec)
        if not html:
            continue
        ts = rec["timestamp"]
        snap_date = date(int(ts[:4]), int(ts[4:6]), int(ts[6:8]))
        df = parse_injury_list_html(html, fallback_date=snap_date)
        if df.empty:
            continue
        df["source"] = _CC_SOURCE
        frames.append(df)
        print(f"[commoncrawl] {i + 1}/{len(records)} {ts[:8]} -> {len(df)} rows")
        time.sleep(sleep_s)

    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, ignore_index=True)
    out = out.drop_duplicates(subset=["list_date", "team", "player_name_norm"], keep="first")
    print(
        f"[commoncrawl] total {len(out)} entries across {out['list_date'].nunique()} dates"
    )
    return out


def fetch_wayback_injury_lists(
    *,
    from_year: int = 2021,
    to_year: int | None = None,
    limit: int = 80,
    sleep_s: float = 1.5,
    use_cache: bool = True,
    use_common_crawl: bool = True,
) -> pd.DataFrame:
    to_year = to_year or date.today().year
    frames: list[pd.DataFrame] = []

    if use_common_crawl and from_year <= 2022:
        cc_end = min(to_year, 2022)
        cc_df = fetch_common_crawl_injury_lists(from_year=from_year, to_year=cc_end)
        if not cc_df.empty:
            frames.append(cc_df)

    snapshots = query_wayback_cdx(
        from_year=from_year, to_year=to_year, limit=limit, use_cache=use_cache
    )
    wayback_blocked = False
    for i, snap in enumerate(snapshots):
        if wayback_blocked:
            break
        ts = snap["timestamp"]
        html = fetch_wayback_snapshot(timestamp=ts)
        if not html:
            if i == 0:
                print("[wayback] web.archive.org unreachable — skipping remaining snapshots")
                wayback_blocked = True
            continue
        snap_date = date(int(ts[:4]), int(ts[4:6]), int(ts[6:8]))
        df = parse_injury_list_html(html, fallback_date=snap_date)
        if df.empty:
            continue
        df["source"] = _SOURCE
        frames.append(df)
        print(f"[wayback] {i + 1}/{len(snapshots)} {ts[:8]} -> {len(df)} rows")
        time.sleep(sleep_s)

    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, ignore_index=True)
    out = out.drop_duplicates(subset=["list_date", "team", "player_name_norm"], keep="first")
    print(f"[wayback+cc] combined {len(out)} entries, {out['list_date'].nunique()} dates")
    return out
