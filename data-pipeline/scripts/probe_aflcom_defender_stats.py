"""Probe AFL.com match stats keys for intercept marks, clearances, spoils."""
import json
import sys
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from data_pipeline.ingest.afl_com import (
    _HEADERS,
    CFS_API,
    fetch_season_matches,
    get_afl_token,
    load_afl_com_player_games,
)

TARGETS = {"James Sicily", "Tom Barrass"}


def dump_match_stats(match: dict, token: str) -> None:
    provider_id = match.get("providerId")
    resp = requests.get(
        f"{CFS_API}/playerStats/match/{provider_id}",
        headers={**_HEADERS, "x-media-mis-token": token},
        timeout=30,
    )
    resp.raise_for_status()
    payload = resp.json()

    round_no = match.get("round", {}).get("roundNumber")
    home = match.get("home", {}).get("team", {}).get("club", {}).get("name")
    away = match.get("away", {}).get("team", {}).get("club", {}).get("name")
    print(f"\n=== R{round_no} {home} v {away} ({provider_id}) ===")

    for team_key in ("homeTeamPlayerStats", "awayTeamPlayerStats"):
        for entry in payload.get(team_key, []):
            ps = entry.get("playerStats", {})
            player = ps.get("player", {})
            pname = player.get("playerName", {})
            name = f"{pname.get('givenName', '')} {pname.get('surname', '')}".strip()
            if name not in TARGETS:
                continue
            stats = ps.get("stats", {}) or {}
            print(f"\n--- {name} ---")
            ext = stats.get("extendedStats")
            if ext:
                print(f"  extendedStats keys: {sorted(ext.keys()) if isinstance(ext, dict) else ext!r}")
                if isinstance(ext, dict):
                    for k, v in sorted(ext.items()):
                        if any(x in k.lower() for x in ("mark", "clear", "spoil", "intercept", "one", "smother")):
                            print(f"    ext.{k}: {v!r}")
            for key in (
                "interceptMarks", "intercepts", "clearances", "centreClearances",
                "stoppageClearances", "spoils", "onePercenters", "marks",
                "contestedMarks", "marksInside50", "disposals",
            ):
                if key in stats:
                    print(f"  {key}: {stats[key]!r}")
            # Any key containing mark, clear, spoil, intercept
            interesting = {
                k: v for k, v in stats.items()
                if any(x in k.lower() for x in ("mark", "clear", "spoil", "intercept", "one"))
            }
            if interesting:
                print("  [filtered keys]")
                for k, v in sorted(interesting.items()):
                    print(f"    {k}: {v!r}")


def main() -> None:
    print("=== Cached parquet columns & sample ===")
    cache = Path(__file__).resolve().parents[1] / "raw" / "afl_com_player_games_2026.parquet"
    if cache.exists():
        df = pd.read_parquet(cache)
        print("columns:", list(df.columns))
        for name in TARGETS:
            sub = df[df["player_name"] == name]
            if sub.empty:
                print(f"{name}: not in cache")
                continue
            print(f"\n{name} cached averages:")
            for col in ("intercept_marks", "intercepts", "clearances", "contested_marks", "disposals"):
                if col in sub.columns:
                    print(f"  {col}: mean={sub[col].mean():.2f} max={sub[col].max()}")

    print("\n=== Live API: Hawthorn matches ===")
    matches = fetch_season_matches(2026)
    token = get_afl_token()
    haw = [
        m for m in matches
        if "Hawthorn" in str(m.get("home", {})) or "Hawthorn" in str(m.get("away", {}))
    ]
    for m in haw[:3]:
        dump_match_stats(m, token)

    # Sample one match stat keys for any player
    if haw:
        provider_id = haw[0]["providerId"]
        resp = requests.get(
            f"{CFS_API}/playerStats/match/{provider_id}",
            headers={**_HEADERS, "x-media-mis-token": token},
            timeout=30,
        )
        stats0 = resp.json()["homeTeamPlayerStats"][0]["playerStats"]["stats"]
        print("\n=== All stat keys in first home player ===")
        print(sorted(stats0.keys()))


if __name__ == "__main__":
    main()
