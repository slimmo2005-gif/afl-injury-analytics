"""Ingest player match participation from Fryzigg (fitzRoy ecosystem)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pyreadr
import requests

from ..config import FRYZIGG_RDS_FILE, FRYZIGG_RDS_URL, MIN_SEASON, TEAM_ALIASES


def normalize_team(name: str) -> str:
    return TEAM_ALIASES.get(name, name)


def parse_round(value: str | float | int | None) -> int | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    if text.isdigit():
        return int(text)
    if text == "Opening Round":
        return 0
    return None


def download_rds(dest: Path = FRYZIGG_RDS_FILE, force: bool = False) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and not force:
        return dest
    print(f"[fryzigg] downloading {FRYZIGG_RDS_URL} …")
    resp = requests.get(FRYZIGG_RDS_URL, timeout=180, headers={"User-Agent": "afl-injury-analytics/0.2"})
    resp.raise_for_status()
    dest.write_bytes(resp.content)
    print(f"[fryzigg] saved {dest} ({len(resp.content) // 1024} KB)")
    return dest


def load_player_games(
    from_season: int = MIN_SEASON,
    to_season: int | None = None,
    rds_path: Path | None = None,
) -> pd.DataFrame:
    path = rds_path or download_rds()
    raw = pyreadr.read_r(str(path))[None]
    raw["match_date"] = pd.to_datetime(raw["match_date"], errors="coerce")
    raw["season"] = raw["match_date"].dt.year
    if to_season is not None:
        raw = raw[(raw["season"] >= from_season) & (raw["season"] <= to_season)]
    else:
        raw = raw[raw["season"] >= from_season]

    raw["round"] = raw["match_round"].map(parse_round)
    raw = raw[raw["round"].notna()].copy()
    raw["round"] = raw["round"].astype(int)

    raw["player_name"] = (
        raw["player_first_name"].astype(str).str.strip()
        + " "
        + raw["player_last_name"].astype(str).str.strip()
    ).str.strip()
    raw["player_id"] = raw["player_id"].astype(str)
    raw["team"] = raw["player_team"].map(normalize_team)

    cols = ["player_id", "player_name", "team", "season", "round", "match_id", "match_date"]
    if "disposals" in raw.columns:
        raw["disposals"] = pd.to_numeric(raw["disposals"], errors="coerce").fillna(0).astype(int)
    else:
        raw["disposals"] = 0
    if "goals" in raw.columns:
        raw["goals"] = pd.to_numeric(raw["goals"], errors="coerce").fillna(0).astype(int)
    else:
        raw["goals"] = 0

    out = raw[cols + ["disposals", "goals"]].drop_duplicates(
        subset=["player_id", "team", "season", "round", "match_id"]
    )
    out["match_date"] = out["match_date"].dt.date
    return out
