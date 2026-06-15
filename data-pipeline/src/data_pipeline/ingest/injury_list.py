"""Scrape AFL.com.au official injury list (weekly snapshot)."""

from __future__ import annotations

import re
from datetime import date, datetime

import pandas as pd
import requests
from bs4 import BeautifulSoup, Tag

from ..config import TEAM_ALIASES

INJURY_LIST_URL = "https://www.afl.com.au/matches/injury-list"
_HEADERS = {
    "User-Agent": "afl-injury-analytics/0.4",
    "Referer": "https://www.afl.com.au/",
}

# Badge image filenames use these codes before _FA
_BADGE_TO_TEAM: dict[str, str] = {
    "ADEL": "Adelaide",
    "BRIS": "Brisbane Lions",
    "CARL": "Carlton",
    "COLL": "Collingwood",
    "ESS": "Essendon",
    "FREM": "Fremantle",
    "GEEL": "Geelong",
    "GCS": "Gold Coast",
    "GWS": "Greater Western Sydney",
    "HAW": "Hawthorn",
    "MELB": "Melbourne",
    "NMFC": "North Melbourne",
    "PA": "Port Adelaide",
    "RICH": "Richmond",
    "STK": "St Kilda",
    "SYD": "Sydney",
    "WCE": "West Coast",
    "WB": "Western Bulldogs",
}

_NON_INJURY_TYPES = frozenset(
    {
        "suspension",
        "personal",
        "personal reasons",
        "managed",
        "rested",
        "rest",
    }
)


def normalize_team(name: str) -> str:
    return TEAM_ALIASES.get(name.strip(), name.strip())


def normalize_player_name(name: str) -> str:
    return re.sub(r"\s+", " ", name.replace("\xa0", " ")).strip().lower()


def categorize_injury(injury_type: str) -> tuple[str, bool]:
    """Return (category, is_injury)."""
    raw = injury_type.strip()
    low = raw.lower()

    if low in _NON_INJURY_TYPES or "suspension" in low:
        return "suspension", False
    if "personal" in low or "managed" in low or low == "rested":
        return "non_injury", False
    if "concussion" in low:
        return "concussion", True
    if any(x in low for x in ("hamstring", "calf", "groin", "ankle", "achilles", "foot", "shin", "toe")):
        return "lower_limb", True
    if any(x in low for x in ("knee", "acl", "mcl", "pcl")):
        return "knee", True
    if any(x in low for x in ("shoulder", "elbow", "wrist", "hand", "finger", "thumb", "bicep", "pectoral")):
        return "upper_limb", True
    if any(x in low for x in ("back", "spine", "rib", "chest", "abdominal", "core")):
        return "torso", True
    if any(x in low for x in ("illness", "virus", "covid")):
        return "illness", True
    if low == "test":
        return "test", True
    return "other", True


def _club_from_badge_src(src: str) -> str | None:
    m = re.search(r"Badge-Refresh_([A-Z]+)(?:_FA|_v2)", src)
    if not m:
        return None
    return _BADGE_TO_TEAM.get(m.group(1))


def _parse_updated_date(text: str) -> date | None:
    m = re.search(r"Updated:\s*([A-Za-z]+\s+\d{1,2},\s*\d{4})", text)
    if not m:
        return None
    try:
        return datetime.strptime(m.group(1), "%B %d, %Y").date()
    except ValueError:
        return None


def _is_injury_table(table: Tag) -> bool:
    headers = [th.get_text(strip=True).upper() for th in table.find_all("th")]
    return "PLAYER" in headers and "INJURY" in headers


def parse_injury_list_html(html: str, *, fallback_date: date | None = None) -> pd.DataFrame:
    """Parse injury tables; club badges are often inside HTML comments."""
    soup = BeautifulSoup(html, "html.parser")
    article = soup.find("article", class_=re.compile("article")) or soup
    body_html = str(article.find(class_=re.compile("article-body")) or article)

    rows: list[dict] = []
    current_list_date: date | None = fallback_date

    for table in article.find_all("table"):
        if not _is_injury_table(table):
            continue

        table_snip = str(table)[:120]
        pos = body_html.find(table_snip)
        current_team: str | None = None
        if pos >= 0:
            badges = list(re.finditer(r"Badge-Refresh_([A-Z]+)(?:_FA|_v2)", body_html[:pos]))
            if badges:
                current_team = _BADGE_TO_TEAM.get(badges[-1].group(1))

        for tr in table.find_all("tr"):
            cells = [td.get_text(strip=True) for td in tr.find_all("td")]
            if len(cells) != 3:
                if len(cells) == 1 and cells[0].startswith("Updated:"):
                    updated = _parse_updated_date(cells[0])
                    if updated:
                        current_list_date = updated
                continue
            if not current_team or not current_list_date:
                continue
            player, injury, est_return = cells
            if player.upper() == "PLAYER":
                continue
            category, is_injury = categorize_injury(injury)
            rows.append(
                {
                    "list_date": current_list_date,
                    "team": normalize_team(current_team),
                    "player_name": player,
                    "player_name_norm": normalize_player_name(player),
                    "injury_type": injury,
                    "injury_category": category,
                    "estimated_return": est_return,
                    "is_injury": is_injury,
                }
            )

    if not rows:
        from .injury_common import parse_sequential_afl_tables

        seq_rows = parse_sequential_afl_tables(html, list_date=fallback_date or date.today())
        if seq_rows:
            return pd.DataFrame(seq_rows)
        return pd.DataFrame()
    return pd.DataFrame(rows)


def fetch_injury_list(*, url: str = INJURY_LIST_URL) -> pd.DataFrame:
    resp = requests.get(url, headers=_HEADERS, timeout=60)
    resp.raise_for_status()
    fallback: date | None = None
    m = re.search(r"Updated:\s*([A-Za-z]+\s+\d{1,2},\s*\d{4})", resp.text)
    if m:
        fallback = _parse_updated_date(f"Updated: {m.group(1)}")
    df = parse_injury_list_html(resp.text, fallback_date=fallback)
    if not df.empty:
        print(f"[injury_list] parsed {len(df)} entries across {df['team'].nunique()} clubs")
    return df


def link_injury_list_players(df: pd.DataFrame, con) -> pd.DataFrame:
    """Attach Fryzigg player_id via name + team match."""
    if df.empty:
        return df
    out = df.copy()
    con.register("_inj", out)
    linked = con.execute(
        """
        SELECT
            i.*,
            (
                SELECT pg.player_id
                FROM player_games pg
                WHERE pg.team = i.team
                  AND LOWER(pg.player_name) = i.player_name_norm
                ORDER BY pg.season DESC
                LIMIT 1
            ) AS player_id
        FROM _inj i
        """
    ).df()
    con.unregister("_inj")

    # Surname fallback for hyphenated / spelling variants
    missing = linked["player_id"].isna()
    if missing.any():
        con.register("_inj2", linked[missing])
        fallback = con.execute(
            """
            SELECT
                i.list_date,
                i.team,
                i.player_name_norm,
                (
                    SELECT pg.player_id
                    FROM player_games pg
                    WHERE pg.team = i.team
                      AND LOWER(regexp_extract(pg.player_name, ' ([^ ]+)$', 1))
                          = LOWER(regexp_extract(i.player_name, ' ([^ ]+)$', 1))
                    ORDER BY pg.season DESC
                    LIMIT 1
                ) AS player_id_fb
            FROM _inj2 i
            """
        ).df()
        con.unregister("_inj2")
        if not fallback.empty:
            linked = linked.merge(
                fallback,
                on=["list_date", "team", "player_name_norm"],
                how="left",
            )
            linked["player_id"] = linked["player_id"].fillna(linked["player_id_fb"])
            linked = linked.drop(columns=["player_id_fb"])

    matched = linked["player_id"].notna().sum()
    print(f"[injury_list] linked {matched}/{len(linked)} entries to player_id")
    return linked


def load_injury_list_entries(con, df: pd.DataFrame, *, replace_date: bool = True) -> None:
    if df.empty:
        return
    if "source" not in df.columns:
        df = df.copy()
        df["source"] = "afl_injury_list"
    df = df.drop_duplicates(subset=["list_date", "team", "player_name_norm"], keep="first")
    if replace_date:
        for row in df[["list_date", "source"]].drop_duplicates().itertuples(index=False):
            d = pd.Timestamp(row.list_date).date()
            con.execute(
                "DELETE FROM injury_list_entries WHERE list_date = ? AND source = ?",
                [d, row.source],
            )
    con.register("_inj_load", df)
    con.execute(
        """
        INSERT INTO injury_list_entries (
            list_date, team, player_name, player_name_norm,
            injury_type, injury_category, estimated_return, is_injury, player_id, source
        )
        SELECT
            list_date,
            team,
            player_name,
            player_name_norm,
            injury_type,
            injury_category,
            estimated_return,
            is_injury,
            player_id,
            source
        FROM _inj_load
        ON CONFLICT (list_date, team, player_name_norm) DO UPDATE SET
            player_name = excluded.player_name,
            injury_type = excluded.injury_type,
            injury_category = excluded.injury_category,
            estimated_return = excluded.estimated_return,
            is_injury = excluded.is_injury,
            player_id = COALESCE(excluded.player_id, injury_list_entries.player_id),
            source = excluded.source
        """
    )
    con.unregister("_inj_load")
    print(f"[injury_list] loaded {len(df)} entries ({df['source'].nunique()} sources)")
