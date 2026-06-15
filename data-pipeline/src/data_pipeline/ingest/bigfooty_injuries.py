"""Scrape BigFooty news articles from the AFL injuries category."""

from __future__ import annotations

import re
import time
from datetime import date

import pandas as pd
import requests

from ..config import BIGFOOTY_INJURIES_CATEGORY
from .injury_common import (
    parse_h3_table_article,
    parse_list_date_from_html,
    parse_round_from_text,
    rows_to_dataframe,
)

_HEADERS = {"User-Agent": "afl-injury-analytics/0.4"}
_SOURCE = "bigfooty_news"


def catalog_injury_articles(*, max_pages: int = 4) -> list[dict]:
    seen: set[str] = set()
    articles: list[dict] = []
    for page in range(1, max_pages + 1):
        url = BIGFOOTY_INJURIES_CATEGORY if page == 1 else f"{BIGFOOTY_INJURIES_CATEGORY}page/{page}/"
        resp = requests.get(url, headers=_HEADERS, timeout=60)
        if resp.status_code != 200:
            break
        from bs4 import BeautifulSoup

        for anchor in BeautifulSoup(resp.text, "html.parser").find_all("a", href=True):
            href = anchor["href"]
            if "bigfooty.com/20" not in href or href in seen:
                continue
            if any(x in href for x in ("category", "uploads", "forum")):
                continue
            seen.add(href)
            title = anchor.get_text(strip=True)
            year_match = re.search(r"/20(\d{2})/", href)
            year = int("20" + year_match.group(1)) if year_match else None
            rnd = parse_round_from_text(href + " " + title)
            articles.append({"url": href, "title": title, "year": year, "round": rnd})
    return articles


def fetch_article_rows(url: str) -> list[dict]:
    resp = requests.get(url, headers=_HEADERS, timeout=60)
    resp.raise_for_status()
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(resp.text, "html.parser")
    fallback = parse_list_date_from_html(soup)
    return parse_h3_table_article(resp.text, fallback_date=fallback)


def fetch_bigfooty_news(
    *,
    min_year: int = 2018,
    max_year: int | None = None,
    max_pages: int = 4,
    sleep_s: float = 0.4,
) -> pd.DataFrame:
    max_year = max_year or date.today().year
    articles = [
        a
        for a in catalog_injury_articles(max_pages=max_pages)
        if a.get("year") and min_year <= a["year"] <= max_year
    ]
    all_rows: list[dict] = []
    for i, article in enumerate(articles):
        try:
            rows = fetch_article_rows(article["url"])
            if rows:
                all_rows.extend(rows)
                print(
                    f"[bigfooty_news] {i + 1}/{len(articles)} "
                    f"{article.get('year')} R{article.get('round')} -> {len(rows)} rows"
                )
        except Exception as exc:
            print(f"[bigfooty_news] skip {article['url']}: {exc}")
        time.sleep(sleep_s)

    df = rows_to_dataframe(all_rows, source=_SOURCE)
    if not df.empty:
        print(
            f"[bigfooty_news] total {len(df)} entries, "
            f"{df['list_date'].nunique()} dates, {df['team'].nunique()} clubs"
        )
    return df


def fetch_recent_bigfooty_news(*, pages: int = 1) -> pd.DataFrame:
    """Lightweight fetch for pipeline cron — first category page only."""
    return fetch_bigfooty_news(min_year=date.today().year - 1, max_pages=pages, sleep_s=0.2)
