"""Build frontend/public/data/colemanWinnersHeights.json from CSV export."""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
CSV_PATH = ROOT / "shared" / "output" / "exports" / "coleman_winners_heights.csv"
OUT_PATH = ROOT / "frontend" / "public" / "data" / "colemanWinnersHeights.json"

# Wikimedia Commons (CC-licensed). Local path preferred when cached under frontend/public/coleman/.
PHOTOS: dict[str, str] = {
    "Roy Park": "coleman/roy-park.svg",
    "Nick Watson": "https://upload.wikimedia.org/wikipedia/commons/8/8a/NickWatson2.jpg",
    "Harry McKay": "https://upload.wikimedia.org/wikipedia/commons/4/4e/Harry_McKay_2019.1.jpg",
    "Malcolm Blight": "https://upload.wikimedia.org/wikipedia/commons/5/5e/Malcolm_Blight_2014.jpg",
    "Jeremy Cameron": "https://upload.wikimedia.org/wikipedia/commons/1/1e/Jeremy_Cameron_2019.1.jpg",
    "Charlie Curnow": "https://upload.wikimedia.org/wikipedia/commons/8/8d/Charlie_Curnow_2019.1.jpg",
    "Tom Hawkins": "https://upload.wikimedia.org/wikipedia/commons/0/0c/Tom_Hawkins_2019.1.jpg",
    "Lance Franklin": "https://upload.wikimedia.org/wikipedia/commons/7/7e/Lance_Franklin_2019.1.jpg",
    "Tony Lockett": "https://upload.wikimedia.org/wikipedia/commons/2/2a/Tony_Lockett.jpg",
    "Jason Dunstall": "https://upload.wikimedia.org/wikipedia/commons/6/6e/Jason_Dunstall.jpg",
    "Peter Hudson": "https://upload.wikimedia.org/wikipedia/commons/3/3e/Peter_Hudson_%28cropped%29.jpg",
    "John Coleman": "https://upload.wikimedia.org/wikipedia/commons/5/5a/John_Coleman_%28Australian_footballer%29.jpg",
    "Leigh Matthews": "https://upload.wikimedia.org/wikipedia/commons/9/9e/Leigh_Matthews_2014.jpg",
    "Dick Harris": "https://upload.wikimedia.org/wikipedia/commons/6/6a/Dick_Harris_%28footballer%29.jpg",
}

NICKNAMES: dict[str, str] = {
    "Roy Park": "Little Doc",
}

NOTES: dict[str, str] = {
    "Roy Park": "Led VFL goalkicking for winless University in 1913. Retrospective Coleman equivalent.",
    "Vin Coutie": "No reliable height recorded in historical sources.",
    "Malcolm Blight": "Last Coleman Medallist under 183 cm (1982).",
    "Harry McKay": "Tallest recorded Coleman Medallist (204 cm).",
}

CHALLENGER = {
    "player": "Nick Watson",
    "club": "Hawthorn",
    "height_cm": 170,
    "current_goals": 36,
    "coleman_position": 3,
    "photo_url": "https://upload.wikimedia.org/wikipedia/commons/8/8a/NickWatson2.jpg",
    "notes": "2026 season in progress. Goals and ladder position updated manually.",
}


def _height(val) -> int | None:
    if pd.isna(val):
        return None
    return int(float(val))


def main() -> None:
    df = pd.read_csv(CSV_PATH)
    winners = []
    for _, row in df.iterrows():
        player = str(row["player"])
        height = _height(row.get("height_cm"))
        winners.append(
            {
                "year": int(row["season"]),
                "player": player,
                "club": str(row["club"]),
                "height_cm": height,
                "goals": int(row["goals_home_away"]),
                "photo_url": PHOTOS.get(player),
                "notes": NOTES.get(player),
                "nickname": NICKNAMES.get(player),
                "coleman_medal": bool(row.get("coleman_medal_era", False)),
                "season_incomplete": bool(row.get("season_incomplete", False)),
                "tied_winner": bool(row.get("tied_winner", False)),
            }
        )

    payload = {
        "meta": {
            "generatedAt": datetime.now(tz=UTC).isoformat(),
            "source": "AFL Tables via coleman_winners_heights.csv",
            "description": "VFL/AFL leading goalkickers and Coleman Medallists with recorded heights",
        },
        "challenger": CHALLENGER,
        "winners": sorted(winners, key=lambda w: w["year"], reverse=True),
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {OUT_PATH} ({len(winners)} winners)")


if __name__ == "__main__":
    main()
