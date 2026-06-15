"""Scrape Adelaide and Port Adelaide SANFL match reports / team selections."""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urljoin, urlparse

import pandas as pd
import requests
from bs4 import BeautifulSoup

from ..config import MIN_SEASON, ROOT
from .sanfl import fetch_sanfl_fixtures, load_sanfl_club_map
from .vfl import normalize_player_name

USER_AGENT = "afl-injury-analytics/0.3"
ARTICLE_PATH_CACHE = ROOT / "shared" / "data" / "sanfl_club_article_paths.json"
ROUND_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
    "twenty-one": 21,
}
OPPONENT_SLUGS: dict[str, str] = {
    "north-adelaide": "North Adelaide",
    "port-adelaide": "Port Adelaide",
    "sturt": "Sturt",
    "glenelg": "Glenelg",
    "south-adelaide": "South Adelaide",
    "west-adelaide": "West Adelaide",
    "central-district": "Central District",
    "central-districts": "Central District",
    "norwood": "Norwood",
    "woodville-west-torrens": "Woodville-West Torrens",
    "wwt": "Woodville-West Torrens",
}
BAD_NAME_TOKENS = {
    "round",
    "western",
    "bulldogs",
    "showdown",
    "injury",
    "return",
    "season",
    "premiership",
    "highlights",
}
SANFL_TEAM_CODES = {"GLG": "Glenelg", "PA": "Port Adelaide", "ADE": "Adelaide"}
SKIP_NAMES = {
    "north adelaide",
    "south adelaide",
    "west adelaide",
    "port adelaide",
    "central district",
    "woodville-west torrens",
    "jacob surjan",
    "matthew wright",
    "zac standish",
    "ben filosi",
    "joe walker",
    "dejan kalinic",
    "russell ebert",
    "brock pearson",
    "callum mills",
    "riley bice",
    "isaac heeney",
    "liam mcbean",
    "angus schumacher",
}


@dataclass(frozen=True)
class ClubSource:
    key: str
    base_url: str
    afl_club: str
    state_team: str
    catalog_urls: tuple[str, ...]
    link_pattern: re.Pattern[str]


CLUBS: tuple[ClubSource, ...] = (
    ClubSource(
        key="afc",
        base_url="https://www.afc.com.au",
        afl_club="Adelaide",
        state_team="Adelaide",
        catalog_urls=("https://www.afc.com.au/teams/sanfl/news",),
        link_pattern=re.compile(
            r"/news/\d+/(?:sanfl-[^\"']+|[^\"']*sanfl[^\"']*)",
            re.I,
        ),
    ),
    ClubSource(
        key="port",
        base_url="https://www.portadelaidefc.com.au",
        afl_club="Port Adelaide",
        state_team="Port Adelaide",
        catalog_urls=("https://www.portadelaidefc.com.au/teams/sanfl",),
        link_pattern=re.compile(
            r"/news/\d+/(?:[^\"']*magpies[^\"']*|[^\"']*sanfl[^\"']*)",
            re.I,
        ),
    ),
)


def _headers() -> dict[str, str]:
    return {"User-Agent": USER_AGENT}


def _article_id(url: str) -> str | None:
    m = re.search(r"/news/(\d+)/", url)
    return m.group(1) if m else None


def _probe_news_id(club: ClubSource, news_id: int) -> str | None:
    url = f"{club.base_url}/news/{news_id}/"
    try:
        resp = requests.get(url, headers=_headers(), timeout=12, allow_redirects=True)
    except requests.RequestException:
        return None
    if resp.status_code != 200:
        return None
    path = urlparse(resp.url).path
    if re.fullmatch(r"/news/\d+/?", path):
        soup = BeautifulSoup(resp.text, "html.parser")
        canonical = soup.find("link", rel="canonical")
        if canonical and canonical.get("href"):
            path = urlparse(canonical["href"]).path
    if not club.link_pattern.search(path):
        return None
    slug = path.rsplit("/", 1)[-1]
    if club.key == "afc" and "sanfl" not in slug.lower():
        return None
    if club.key == "port" and "magpies" not in slug.lower() and "sanfl" not in slug.lower():
        return None
    return path


def _load_path_cache() -> dict[str, list[str]]:
    if not ARTICLE_PATH_CACHE.exists():
        return {}
    try:
        return json.loads(ARTICLE_PATH_CACHE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_path_cache(paths_by_club: dict[str, list[str]]) -> None:
    ARTICLE_PATH_CACHE.parent.mkdir(parents=True, exist_ok=True)
    ARTICLE_PATH_CACHE.write_text(json.dumps(paths_by_club, indent=2), encoding="utf-8")


def discover_article_paths(club: ClubSource, *, pause: float = 0.15, refresh: bool = False) -> list[str]:
    """Collect SANFL article paths from catalog pages, ID neighbors, and cross-links."""
    cache = _load_path_cache()
    if not refresh and club.key in cache and cache[club.key]:
        return cache[club.key]

    seen: set[str] = set()
    queue: list[str] = []
    seed_ids: list[int] = []

    for catalog in club.catalog_urls:
        resp = requests.get(catalog, headers=_headers(), timeout=45)
        resp.raise_for_status()
        for match in club.link_pattern.finditer(resp.text):
            path = match.group(0).split('"')[0].split("'")[0]
            if path not in seen:
                seen.add(path)
                queue.append(path)
                if nid := _article_id(path):
                    seed_ids.append(int(nid))
        time.sleep(pause)

    sorted_ids = sorted(set(seed_ids))
    for lo, hi in zip(sorted_ids, sorted_ids[1:]):
        gap = hi - lo
        if gap < 250 or gap > 2500:
            continue
        if lo < 2040000:
            continue
        for nid in range(lo + 1, hi):
            path = _probe_news_id(club, nid)
            if path and path not in seen:
                seen.add(path)
                queue.append(path)
            time.sleep(pause / 8)

    for path in list(queue):
        url = urljoin(club.base_url, path)
        try:
            resp = requests.get(url, headers=_headers(), timeout=45)
        except requests.RequestException:
            continue
        if resp.status_code != 200:
            continue
        for match in club.link_pattern.finditer(resp.text):
            rel = match.group(0).split('"')[0].split("'")[0]
            if rel not in seen:
                seen.add(rel)
                queue.append(rel)
        time.sleep(pause)

    result = sorted(set(queue))
    cache[club.key] = result
    _save_path_cache(cache)
    return result


def _extract_article_text(html: str) -> tuple[str, str, str | None]:
    soup = BeautifulSoup(html, "html.parser")
    title_el = soup.find("h1")
    title = title_el.get_text(" ", strip=True) if title_el else ""
    article = (
        soup.find("article")
        or soup.select_one(".article-body, .content-body, .rich-text, .article-content")
    )
    text = (article or soup).get_text("\n", strip=True).replace("\ufffd", "'")
    published: str | None = None
    time_el = soup.find("time")
    if time_el and time_el.get("datetime"):
        published = time_el["datetime"][:10]
    return title, text, published


def _word_round(token: str) -> int | None:
    token = token.strip().lower().replace("-", " ")
    if token.isdigit():
        return int(token)
    if token in ROUND_WORDS:
        return ROUND_WORDS[token]
    parts = token.split()
    if len(parts) == 2 and parts[0] == "twenty" and parts[1] in ROUND_WORDS:
        return 20 + ROUND_WORDS[parts[1]]
    return None


def parse_state_round(slug: str, title: str, text: str) -> int | None:
    slug_l = slug.lower()
    m = re.search(r"round-(\d{1,2})-", slug_l)
    if m:
        return int(m.group(1))
    m = re.search(r"round-([a-z]+)-", slug_l)
    if m:
        val = _word_round(m.group(1))
        if val:
            return val

    blob = f"{slug} {title} {text[:2000]}".lower()
    m = re.search(r"round[\s-]+(\d{1,2})\b", blob)
    if m:
        return int(m.group(1))
    m = re.search(r"round[\s-]+([a-z\-]+)\b", blob)
    if m:
        val = _word_round(m.group(1))
        if val:
            return val
    m = re.search(r"\bround\s+(\d{1,2})\s+sanfl\b", blob)
    if m:
        return int(m.group(1))
    return None


def parse_opponent(slug: str, title: str, text: str) -> str | None:
    slug_l = slug.lower()
    for token, team in OPPONENT_SLUGS.items():
        if f"-v-{token}" in slug_l or f"-vs-{token}" in slug_l or f"-v-{token.replace('-', '-')}" in slug_l:
            return team
    m = re.search(r"\b(?:v|vs|versus)\s+([A-Za-z][A-Za-z\s\-]+)", title, re.I)
    if m:
        guess = m.group(1).strip()
        for team in OPPONENT_SLUGS.values():
            if team.lower() in guess.lower():
                return team
    m = re.search(r"SANFL Highlights:\s*([A-Za-z\s]+?)\s+v\s+([A-Za-z\s]+)", text)
    if m:
        away = m.group(2).strip()
        home = m.group(1).strip()
        for team in (home, away):
            if team in OPPONENT_SLUGS.values() or team in {"Adelaide", "Port Adelaide"}:
                if team not in {"Adelaide", "Port Adelaide"}:
                    return team
    for code, team in SANFL_TEAM_CODES.items():
        if re.search(rf"\b{code}\b", text):
            if team not in {"Adelaide", "Port Adelaide"}:
                return team
    return None


def is_sanfl_article(club: ClubSource, slug: str, title: str, text: str) -> bool:
    blob = f"{slug} {title} {text[:2500]}".lower()
    if "sanfl" in blob:
        return True
    if club.key == "port":
        if "toyota afl premiership" in blob or "afl photos" in blob and "sanfl" not in blob:
            return False
        if "magpies" in slug.lower() and "match-report" in slug.lower():
            return True
        if "sanfl highlights" in blob or "sanfl clash" in blob:
            return True
        return False


def _clean_name(token: str) -> str | None:
    name = normalize_player_name(token.strip(" .,;:"))
    name = name.replace("\u2019", "'").replace("\ufffd", "'")
    if name.lower().startswith("captain "):
        name = name[8:].strip()
    if name.lower().startswith("by "):
        return None
    if not name or len(name) < 3:
        return None
    if name.lower() in SKIP_NAMES:
        return None
    if any(tok.lower() in BAD_NAME_TOKENS for tok in name.split()):
        return None
    parts = name.split()
    if len(parts) == 2 and len(parts[0]) <= 3:
        return None
    if any(word in name.lower() for word in ("adelaide", "magpies", "tigers", "roosters", "eagles", "bloods")):
        return None
    if not re.match(r"^[A-Z][a-z]+(?:\s+[A-Z][A-Za-z'\-]+)+$", name):
        return None
    return name


def _parse_player_tokens(chunk: str) -> set[str]:
    names: set[str] = set()
    for part in re.split(r",\s*|\band\b", chunk):
        part = part.strip().strip(".")
        if not part:
            continue
        m = re.match(r"^([A-Za-z][A-Za-z'\-]*(?:\s+[A-Za-z][A-Za-z'\-]*)?)", part)
        if not m:
            continue
        cleaned = _clean_name(m.group(1))
        if cleaned:
            names.add(cleaned)
    return names


def _names_from_blob(blob: str) -> set[str]:
    names: set[str] = set()
    compact = re.sub(r"\s+", " ", blob.replace("\n", " "))
    for m in re.finditer(
        r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z'\-]+)+)\b",
        compact,
    ):
        cleaned = _clean_name(m.group(1))
        if cleaned:
            names.add(cleaned)
    return names


def _expand_surname_stat(text: str, surname: str) -> str | None:
    idx = text.find(f"{surname} finished with")
    if idx < 0:
        return None
    window = text[max(0, idx - 500) : idx]
    for m in re.finditer(
        rf"\b([A-Z][a-z]+)\s+{re.escape(surname)}\b",
        window,
    ):
        cleaned = _clean_name(f"{m.group(1)} {surname}")
        if cleaned:
            return cleaned
    return _clean_name(surname)


def parse_players(slug: str, title: str, text: str) -> set[str]:
    players: set[str] = set()
    slug_l = slug.lower()
    compact = re.sub(r"\s+", " ", text.replace("\n", " "))

    for m in re.finditer(
        r"([A-Z][a-z]+(?:\s+[A-Z][a-z'\-]+)+)\s+finished\s+with\s+\d+\s+disposals",
        compact,
    ):
        cleaned = _clean_name(m.group(1))
        if cleaned:
            players.add(cleaned)

    for m in re.finditer(r"\b([A-Z][a-z]+)\s+finished\s+with\s+\d+\s+disposals", compact):
        full = _expand_surname_stat(compact, m.group(1))
        if full:
            players.add(full)

    for m in re.finditer(
        r"([A-Z][a-z]+(?:\s+[A-Z][a-z'\-]+)+)\s*\(\s*\d+\s+disposals",
        compact,
    ):
        cleaned = _clean_name(m.group(1))
        if cleaned:
            players.add(cleaned)

    for m in re.finditer(r"(?:Goals|Best):\s*([^\n]+)", text):
        players.update(_parse_player_tokens(m.group(1)))

    if "team-selection" in slug_l or "team selection" in title.lower():
        for pat in (
            r"They include\s*(.+?)(?:\.|come out|will also|The Club)",
            r"AFL-listed players including\s*(.+?)(?:\.|SANFL-listed)",
            r"fellow AFL-listed players including\s*(.+?)(?:\.|SANFL-listed)",
            r"among\s+\d+\s+AFL-listed players[^.]*\.\s*(.+?)(?:\.|Mitch Hinge|come out)",
            r"named to take on[^.]*\.\s*(?:They include\s*)?(.+?)(?:\.|come out)",
            r"will make their return[^.]*\.\s*(.+?)(?:\.|SANFL-listed|Ah Chee)",
            r"return from injury through the SANFL[^.]*\.\s*(.+?)(?:\.|has been)",
        ):
            for m in re.finditer(pat, compact, re.I):
                players.update(_names_from_blob(m.group(1)))
        for m in re.finditer(
            r"([A-Z][a-z]+(?:\s+[A-Z][a-z'\-]+)+)\s+will make their return",
            compact,
        ):
            cleaned = _clean_name(m.group(1))
            if cleaned:
                players.add(cleaned)

    return players


def _infer_season(published: str | None, state_round: int | None) -> int | None:
    if not published:
        return None
    year = int(published[:4])
    month = int(published[5:7])
    if month <= 2 and state_round and state_round >= 15:
        return year - 1
    return year


def _match_fixture(
    fixtures: list[dict],
    *,
    state_team: str,
    state_round: int,
    opponent: str | None,
    game_date: str | None,
) -> dict | None:
    candidates = [f for f in fixtures if f["state_round"] == state_round]
    if opponent:
        narrowed = [
            f
            for f in candidates
            if opponent in {f["home_team"], f["away_team"]}
            and state_team in {f["home_team"], f["away_team"]}
        ]
        if narrowed:
            candidates = narrowed
    else:
        candidates = [f for f in candidates if state_team in {f["home_team"], f["away_team"]}]
    if not candidates:
        return None
    if game_date and len(candidates) > 1:
        dated = [f for f in candidates if f.get("game_date") == game_date]
        if dated:
            return dated[0]
    return candidates[0]


def fetch_club_report_articles(
    *,
    pause: float = 0.15,
    refresh_paths: bool = False,
) -> list[dict]:
    articles: list[dict] = []
    for club in CLUBS:
        paths = discover_article_paths(club, pause=pause, refresh=refresh_paths)
        print(f"[sanfl_club] {club.key}: discovered {len(paths)} article paths")
        for path in paths:
            url = urljoin(club.base_url, path)
            slug = path.split("/", 2)[-1] if path.count("/") >= 2 else path
            try:
                resp = requests.get(url, headers=_headers(), timeout=60)
                resp.raise_for_status()
            except requests.RequestException as exc:
                print(f"[sanfl_club] warning: {url}: {exc}")
                continue
            title, text, published = _extract_article_text(resp.text)
            if not is_sanfl_article(club, slug, title, text):
                continue
            state_round = parse_state_round(slug, title, text)
            if state_round is None:
                continue
            players = parse_players(slug, title, text)
            if not players:
                continue
            articles.append(
                {
                    "club": club.key,
                    "afl_club": club.afl_club,
                    "state_team": club.state_team,
                    "article_id": _article_id(url),
                    "article_url": resp.url,
                    "slug": slug,
                    "title": title,
                    "published": published,
                    "state_round": state_round,
                    "opponent": parse_opponent(slug, title, text),
                    "players": sorted(players),
                }
            )
            time.sleep(pause)
    return articles


def club_articles_to_games(
    articles: list[dict],
    *,
    from_season: int,
    to_season: int,
) -> pd.DataFrame:
    fixtures_by_season: dict[int, list[dict]] = {}
    rows: list[dict] = []

    for article in articles:
        season = _infer_season(article.get("published"), article["state_round"])
        if season is None or season < from_season or season > to_season:
            continue
        if season not in fixtures_by_season:
            fixtures_by_season[season] = fetch_sanfl_fixtures(season, afl_clubs_only=False)
        fixture = _match_fixture(
            fixtures_by_season[season],
            state_team=article["state_team"],
            state_round=article["state_round"],
            opponent=article.get("opponent"),
            game_date=article.get("published"),
        )
        if fixture:
            game_slug = fixture["game_slug"]
            game_date = fixture.get("game_date")
        else:
            game_slug = f"sanfl-club-{article['club']}-{article['article_id']}"
            game_date = article.get("published")

        for player in article["players"]:
            norm = normalize_player_name(player)
            rows.append(
                {
                    "competition": "sanfl",
                    "season": season,
                    "state_round": article["state_round"],
                    "state_team": article["state_team"],
                    "afl_club": article["afl_club"],
                    "player_name": norm,
                    "player_name_norm": norm.lower(),
                    "game_slug": game_slug,
                    "game_date": game_date,
                    "source": f"sanfl_club_{article['club']}",
                }
            )

    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    return df.drop_duplicates(
        subset=["competition", "season", "game_slug", "player_name_norm", "state_team"]
    )


def fetch_sanfl_club_report_games(
    from_season: int,
    to_season: int | None = None,
    *,
    pause: float = 0.15,
) -> pd.DataFrame:
    to_season = to_season or datetime.now().year
    articles = fetch_club_report_articles(pause=pause)
    print(f"[sanfl_club] parsed {len(articles)} SANFL articles with players")
    if not articles:
        return pd.DataFrame()
    df = club_articles_to_games(articles, from_season=from_season, to_season=to_season)
    club_map = load_sanfl_club_map()
    if club_map and not df.empty:
        df["afl_club"] = df["state_team"].map(club_map).fillna(df["afl_club"])
    return df
