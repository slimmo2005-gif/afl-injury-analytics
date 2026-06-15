"""Scrape BigFooty forum threads with full AFL injury list tables."""

from __future__ import annotations

import re
import time
from datetime import date, datetime

import pandas as pd
import requests
from bs4 import BeautifulSoup

from ..config import BIGFOOTY_FORUM_THREADS
from .injury_common import parse_forum_post_tables, rows_to_dataframe

_HEADERS = {"User-Agent": "afl-injury-analytics/0.4"}
_SOURCE = "bigfooty_forum"
_MIN_TABLES_FOR_FULL_LIST = 5


def _thread_base_url(slug: str) -> str:
    return f"https://www.bigfooty.com/forum/threads/{slug}"


def _post_list_date(time_tag) -> date | None:
    if not time_tag or not time_tag.get("datetime"):
        return None
    try:
        return datetime.fromisoformat(time_tag["datetime"].replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _max_forum_pages(soup: BeautifulSoup) -> int | None:
    last = soup.find("a", string=re.compile(r"^Last$", re.I))
    if last and last.get("href"):
        m = re.search(r"/page-(\d+)", last["href"])
        if m:
            return int(m.group(1))
    nums: list[int] = []
    for el in soup.select(".pageNav-page"):
        text = el.get_text(strip=True)
        if text.isdigit():
            nums.append(int(text))
    return max(nums) if nums else None


def crawl_forum_thread(slug: str, *, max_pages: int = 30, sleep_s: float = 0.35) -> list[dict]:
    all_rows: list[dict] = []
    base = _thread_base_url(slug)
    last_page: int | None = None
    for page in range(1, max_pages + 1):
        if last_page is not None and page > last_page:
            break
        url = base if page == 1 else f"{base}/page-{page}"
        resp = requests.get(url, headers=_HEADERS, timeout=60)
        if resp.status_code != 200:
            break
        soup = BeautifulSoup(resp.text, "html.parser")
        if page == 1:
            last_page = _max_forum_pages(soup)
            if last_page:
                print(f"[bigfooty_forum] {slug}: {last_page} pages")
        posts = soup.select("article.message--post")
        if not posts:
            break

        page_rows = 0
        for post in posts:
            body = post.find(class_=re.compile("bbWrapper"))
            if not body:
                continue
            tables = body.find_all("table")
            if len(tables) < _MIN_TABLES_FOR_FULL_LIST:
                continue
            list_date = _post_list_date(post.find("time"))
            if not list_date:
                continue
            rows = parse_forum_post_tables(body, list_date=list_date)
            if rows:
                all_rows.extend(rows)
                page_rows += len(rows)

        print(f"[bigfooty_forum] {slug} page {page}: {page_rows} rows")
        time.sleep(sleep_s)

        if page_rows == 0 and page > 1:
            break

    return all_rows


def fetch_bigfooty_forum(
    *,
    years: list[int] | None = None,
    sleep_s: float = 0.35,
) -> pd.DataFrame:
    years = years or sorted(BIGFOOTY_FORUM_THREADS)
    all_rows: list[dict] = []
    for year in years:
        slug = BIGFOOTY_FORUM_THREADS.get(year)
        if not slug:
            continue
        try:
            rows = crawl_forum_thread(slug, sleep_s=sleep_s)
            all_rows.extend(rows)
            print(f"[bigfooty_forum] {year}: {len(rows)} rows from thread")
        except Exception as exc:
            print(f"[bigfooty_forum] {year} failed: {exc}")

    df = rows_to_dataframe(all_rows, source=_SOURCE)
    if not df.empty:
        print(
            f"[bigfooty_forum] total {len(df)} entries, "
            f"{df['list_date'].nunique()} snapshot dates"
        )
    return df
