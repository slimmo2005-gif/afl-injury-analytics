"""Export every VFL/AFL leading goalkicker (Coleman equivalent) with player height.

Data source: AFL Tables (https://afltables.com/afl/stats/alltime/leadinggk.html)
Heights scraped from individual player profile pages.
"""
from __future__ import annotations

import re
import time
from pathlib import Path
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup

BASE = "https://afltables.com/afl/stats/alltime/leadinggk.html"
PLAYER_URL_BASE = BASE  # ../players/ links resolve under /afl/stats/players/
OUT_DIR = Path(__file__).resolve().parents[2] / "shared" / "output" / "exports"
SESSION = requests.Session()
SESSION.headers.update(
    {"User-Agent": "Mozilla/5.0 (compatible; afl-analytics-research/1.0)"}
)

# Verified AFL.com heights where AFL Tables differs (completed Coleman Medallists only).
AFLCOM_HEIGHT_CM: dict[str, int] = {
    "Harry McKay": 200,
    "Charlie Curnow": 194,
    "Jesse Hogan": 196,
    "Tom Hawkins": 197,
}


def fetch(url: str, retries: int = 3) -> str:
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            resp = SESSION.get(url, timeout=30)
            resp.raise_for_status()
            return resp.text
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            time.sleep(0.5 * (attempt + 1))
    raise RuntimeError(f"Failed to fetch {url}: {last_err}")


def parse_height_cm(html: str) -> int | None:
    m = re.search(r"Height:.*?(\d+)\s*cm", html, re.I | re.DOTALL)
    return int(m.group(1)) if m else None


def cm_to_ft_in(cm: int | None) -> str | None:
    if cm is None:
        return None
    total_in = round(cm / 2.54)
    feet, inches = divmod(total_in, 12)
    return f"{feet}'{inches}\""


def apply_aflcom_overrides(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for player, cm in AFLCOM_HEIGHT_CM.items():
        mask = df["player"] == player
        if not mask.any():
            continue
        df.loc[mask, "height_cm"] = cm
        df.loc[mask, "height_ft_in"] = cm_to_ft_in(cm)
        df.loc[mask, "under_183cm"] = cm < 183
        df.loc[mask, "under_170cm"] = cm <= 170
    return df


def parse_leading_goalkickers(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    rows: list[dict] = []

    for tr in soup.find_all("tr"):
        cells = tr.find_all("td")
        if len(cells) < 4:
            continue

        year_text = cells[0].get_text(strip=True)
        if not re.fullmatch(r"\d{4}", year_text):
            continue

        year = int(year_text)
        player_link = cells[1].find("a")
        player = cells[1].get_text(strip=True)
        goals_ha = cells[2].get_text(strip=True)
        club = cells[3].get_text(strip=True)
        player_url = (
            urljoin(PLAYER_URL_BASE, player_link["href"])
            if player_link and player_link.get("href")
            else None
        )

        try:
            goals = int(goals_ha)
        except ValueError:
            goals = None

        rows.append(
            {
                "season": year,
                "player": player,
                "club": club,
                "goals_home_away": goals,
                "player_url": player_url,
            }
        )

    return rows


def enrich_heights(rows: list[dict]) -> list[dict]:
    cache: dict[str, int | None] = {}
    out: list[dict] = []

    for i, row in enumerate(rows):
        url = row.get("player_url")
        height_cm: int | None = None
        if url:
            if url not in cache:
                try:
                    cache[url] = parse_height_cm(fetch(url))
                except Exception:
                    cache[url] = None
                time.sleep(0.15)
            height_cm = cache[url]

        season = row["season"]
        out.append(
            {
                **row,
                "height_cm": height_cm,
                "height_ft_in": cm_to_ft_in(height_cm),
                "under_183cm": height_cm < 183 if height_cm is not None else None,
                "under_170cm": height_cm <= 170 if height_cm is not None else None,
                "coleman_medal_era": season >= 1955,
                "award_name": (
                    "Coleman Medal"
                    if season >= 1955
                    else "Leading Goalkicker Medal"
                ),
                "award_presented_live": season >= 1981 and season >= 1955,
                "award_retrospective": season >= 1955 and season < 1981,
                "season_incomplete": season == 2026,
            }
        )

        if (i + 1) % 25 == 0:
            print(f"  processed {i + 1}/{len(rows)} rows...")

    return out


def mark_tied_winners(df: pd.DataFrame) -> pd.DataFrame:
    counts = df.groupby("season")["player"].transform("count")
    df = df.copy()
    df["tied_winner"] = counts > 1
    return df


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print("Fetching leading goalkicker list from AFL Tables...")
    html = fetch(BASE)
    rows = parse_leading_goalkickers(html)
    print(f"Found {len(rows)} winner rows across seasons")

    print("Fetching player heights...")
    enriched = enrich_heights(rows)
    df = mark_tied_winners(pd.DataFrame(enriched))
    df = apply_aflcom_overrides(df)
    df = df.sort_values(["season", "player"], ascending=[False, True]).reset_index(drop=True)

    missing = df["height_cm"].isna().sum()
    print(f"Heights found for {len(df) - missing}/{len(df)} rows ({missing} missing)")

    cols = [
        "season",
        "player",
        "club",
        "goals_home_away",
        "height_cm",
        "height_ft_in",
        "under_183cm",
        "under_170cm",
        "coleman_medal_era",
        "award_name",
        "tied_winner",
        "season_incomplete",
        "player_url",
    ]
    df = df[cols]

    csv_path = OUT_DIR / "coleman_winners_heights.csv"
    xlsx_path = OUT_DIR / "coleman_winners_heights.xlsx"
    df.to_csv(csv_path, index=False)

    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Winners", index=False)
        notes = pd.DataFrame(
            [
                {"field": "source", "value": "AFL Tables leading goalkicker; modern heights corrected from AFL.com where verified"},
                {"field": "coleman_medal_era", "value": "Coleman Medal (1955+): first presented 1981; 1955–1980 recognised retrospectively in 2001"},
                {"field": "leading_goalkicker_medal", "value": "Leading Goalkicker Medal for 1897–1954 league leaders"},
                {"field": "under_183cm", "value": "Strictly under 6 foot (183 cm)"},
                {"field": "under_170cm", "value": "170 cm or shorter (Nick Watson benchmark)"},
                {"field": "2026", "value": "Season in progress at time of export; leader may change"},
                {"field": "tied_winner", "value": "Some early seasons had equal home-and-away leading goalkickers"},
                {"field": "generated", "value": pd.Timestamp.now(tz="UTC").isoformat()},
            ]
        )
        notes.to_excel(writer, sheet_name="Notes", index=False)

        short_df = df.dropna(subset=["height_cm"]).copy()
        short_df["height_cm"] = short_df["height_cm"].astype(int)
        if not short_df.empty:
            short = short_df.nsmallest(15, "height_cm")[
                ["season", "player", "club", "goals_home_away", "height_cm", "height_ft_in"]
            ]
            short.to_excel(writer, sheet_name="Shortest winners", index=False)

    print(f"Wrote {csv_path}")
    print(f"Wrote {xlsx_path}")
    print("\nShortest winners with height data:")
    print(
        df.dropna(subset=["height_cm"])
        .nsmallest(10, "height_cm")[["season", "player", "height_cm", "goals_home_away"]]
        .to_string(index=False)
    )


if __name__ == "__main__":
    main()
