"""Shared helpers for injury list ingest from multiple sources."""

from __future__ import annotations

import re
from datetime import date, datetime

import pandas as pd
from bs4 import BeautifulSoup, Tag

from ..config import TEAM_ALIASES
from .injury_list import categorize_injury, normalize_player_name

AFL_CLUB_TABLE_ORDER = (
    "Adelaide",
    "Brisbane Lions",
    "Carlton",
    "Collingwood",
    "Essendon",
    "Fremantle",
    "Geelong",
    "Gold Coast",
    "Greater Western Sydney",
    "Hawthorn",
    "Melbourne",
    "North Melbourne",
    "Port Adelaide",
    "Richmond",
    "St Kilda",
    "Sydney",
    "West Coast",
    "Western Bulldogs",
)

_AFL_TEAM_NAMES = frozenset(
    {
        "Adelaide",
        "Brisbane",
        "Brisbane Lions",
        "Carlton",
        "Collingwood",
        "Essendon",
        "Fremantle",
        "Geelong",
        "Gold Coast",
        "Gold Coast Suns",
        "Greater Western Sydney",
        "GWS",
        "GWS Giants",
        "Hawthorn",
        "Melbourne",
        "North Melbourne",
        "Port Adelaide",
        "Richmond",
        "St Kilda",
        "Sydney",
        "West Coast",
        "West Coast Eagles",
        "Western Bulldogs",
    }
)

_HEADER_NAMES = frozenset({"name", "player", "injury", "return", "estimated return", "availability / timeframe"})


def normalize_injury_team(name: str) -> str:
    cleaned = re.sub(r"\s+injury\s+news$", "", name.strip(), flags=re.I)
    cleaned = cleaned.replace("\xa0", " ").strip()
    return TEAM_ALIASES.get(cleaned, cleaned)


def _is_team_label(text: str) -> bool:
    t = text.strip()
    if not t or len(t) > 40:
        return False
    if t.endswith(" injury news"):
        return True
    return t in _AFL_TEAM_NAMES


def team_from_table_context(table: Tag) -> str | None:
    """Infer club from plain-text label immediately before a table."""
    node = table.find_previous(string=True)
    steps = 0
    while node and steps < 30:
        text = str(node).strip()
        if text:
            if text.endswith(" injury news"):
                return normalize_injury_team(text)
            if text in _AFL_TEAM_NAMES:
                return normalize_injury_team(text)
            if table.find_previous("table") and node.find_parent("table"):
                break
        node = node.find_previous(string=True)
        steps += 1
    return None


def parse_round_from_text(text: str) -> int | None:
    patterns = [
        r"after\s+(?:afl\s+)?round\s+(\d+)",
        r"leading\s+into\s+round\s+(\d+)",
        r"for\s+round\s+(\d+)",
        r"round\s+(\d+)\s+202\d",
        r"\bR(\d+)\b",
        r"round\s+(\d+)",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.I)
        if m:
            rnd = int(m.group(1))
            if 1 <= rnd <= 30:
                return rnd
    return None


def parse_list_date_from_html(soup: BeautifulSoup) -> date | None:
    time_tag = soup.find("time")
    if time_tag and time_tag.get("datetime"):
        try:
            return datetime.fromisoformat(time_tag["datetime"].replace("Z", "+00:00")).date()
        except ValueError:
            pass
    meta = soup.find("meta", property="article:published_time")
    if meta and meta.get("content"):
        try:
            return datetime.fromisoformat(meta["content"][:19]).date()
        except ValueError:
            pass
    return None


def parse_updated_date(text: str) -> date | None:
    m = re.search(r"Updated:\s*([A-Za-z]+\s+\d{1,2},?\s*\d{4})", text, re.I)
    if not m:
        m = re.search(r"Latest Update:\s*([A-Za-z]+\s+\d{1,2})", text, re.I)
        if m:
            return None
    if not m:
        return None
    for fmt in ("%B %d, %Y", "%B %d %Y", "%d %B %Y"):
        try:
            return datetime.strptime(m.group(1).replace(",", ""), fmt.replace(", %Y", " %Y")).date()
        except ValueError:
            continue
    return None


def parse_injury_table(
    table: Tag,
    *,
    team: str,
    list_date: date,
) -> list[dict]:
    rows: list[dict] = []
    for tr in table.find_all("tr"):
        cells = [c.get_text(strip=True) for c in tr.find_all(["th", "td"])]
        if len(cells) < 3:
            continue
        player, injury, est_return = cells[0], cells[1], cells[2]
        if player.lower() in _HEADER_NAMES or injury.lower() in _HEADER_NAMES:
            continue
        if not player or not injury:
            continue
        category, is_injury = categorize_injury(injury)
        rows.append(
            {
                "list_date": list_date,
                "team": normalize_injury_team(team),
                "player_name": player,
                "player_name_norm": normalize_player_name(player),
                "injury_type": injury,
                "injury_category": category,
                "estimated_return": est_return,
                "is_injury": is_injury,
            }
        )
    return rows


def parse_h3_table_article(html: str, *, fallback_date: date | None = None) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    article = soup.find("article") or soup
    list_date = fallback_date or parse_list_date_from_html(soup)
    rows: list[dict] = []
    team: str | None = None
    for el in article.descendants:
        if getattr(el, "name", None) == "h3":
            team = normalize_injury_team(el.get_text(strip=True))
        elif getattr(el, "name", None) == "table" and team and list_date:
            rows.extend(parse_injury_table(el, team=team, list_date=list_date))
    return rows


def parse_forum_post_tables(html_fragment: Tag, *, list_date: date) -> list[dict]:
    rows: list[dict] = []
    for table in html_fragment.find_all("table"):
        team = team_from_table_context(table)
        if not team:
            continue
        rows.extend(parse_injury_table(table, team=team, list_date=list_date))
    return rows


def parse_sequential_afl_tables(html: str, *, list_date: date) -> list[dict]:
    """Parse AFL.com injury tables when club badges are absent (2021-era pages)."""
    soup = BeautifulSoup(html, "html.parser")
    article = soup.find("article", class_=re.compile("article")) or soup.find("article") or soup
    tables = [
        t
        for t in article.find_all("table")
        if "PLAYER" in t.get_text().upper() and "INJURY" in t.get_text().upper()
    ]
    rows: list[dict] = []
    for idx, table in enumerate(tables[: len(AFL_CLUB_TABLE_ORDER)]):
        team = AFL_CLUB_TABLE_ORDER[idx]
        rows.extend(parse_injury_table(table, team=team, list_date=list_date))
    return rows


def rows_to_dataframe(rows: list[dict], *, source: str) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["source"] = source
    return df.drop_duplicates(subset=["list_date", "team", "player_name_norm"], keep="first")
