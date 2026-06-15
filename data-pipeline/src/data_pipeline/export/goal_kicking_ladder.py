"""Export goal-kicking accuracy ladder (Fryzigg + AFL.com for current season)."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import pyreadr

from ..config import FRYZIGG_RDS_FILE, ROOT
from ..ingest.afl_com import latest_fryzigg_season, load_goal_kicking_player_games
from ..ingest.fryzigg import download_rds, normalize_team


def _mode_team(teams: pd.Series) -> str:
    counts = teams.value_counts()
    return str(counts.index[0]) if len(counts) else ""


def _mode_value(values: pd.Series) -> str:
    counts = values.value_counts()
    return str(counts.index[0]) if len(counts) else ""


def _load_fryzigg_games(
    from_season: int,
    to_season: int,
    rds_path: Path | None = None,
) -> pd.DataFrame:
    path = rds_path or download_rds()
    raw = pyreadr.read_r(str(path))[None]
    raw["match_date"] = pd.to_datetime(raw["match_date"], errors="coerce")
    raw["season"] = raw["match_date"].dt.year
    raw = raw[(raw["season"] >= from_season) & (raw["season"] <= to_season)].copy()

    raw["player_id"] = raw["player_id"].astype(str)
    raw["player_name"] = (
        raw["player_first_name"].astype(str).str.strip()
        + " "
        + raw["player_last_name"].astype(str).str.strip()
    ).str.strip()
    raw["team"] = raw["player_team"].map(normalize_team)

    for col in ("goals", "behinds", "shots_at_goal"):
        raw[col] = pd.to_numeric(raw[col], errors="coerce").fillna(0)

    out = raw[
        [
            "player_id",
            "player_name",
            "team",
            "season",
            "match_id",
            "match_date",
            "goals",
            "behinds",
            "shots_at_goal",
        ]
    ].copy()
    out["source"] = "fryzigg"
    return out


def _load_supplement_games(from_season: int, to_season: int, rds_path: Path) -> pd.DataFrame:
    fryzigg_max = latest_fryzigg_season(rds_path)
    if fryzigg_max is None:
        start = from_season
    else:
        start = max(from_season, fryzigg_max + 1)
    if start > to_season:
        return pd.DataFrame()

    frames = [load_goal_kicking_player_games(season) for season in range(start, to_season + 1)]
    frames = [f for f in frames if not f.empty]
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def load_goal_kicking_games(
    from_season: int,
    to_season: int,
    rds_path: Path | None = None,
) -> pd.DataFrame:
    path = rds_path or download_rds()
    fryzigg = _load_fryzigg_games(from_season, to_season, path)
    supplement = _load_supplement_games(from_season, to_season, path)
    if supplement.empty:
        return fryzigg
    if fryzigg.empty:
        return supplement
    return pd.concat([fryzigg, supplement], ignore_index=True)


def build_goal_kicking_ladder_df(
    from_season: int,
    to_season: int,
    min_shots: int = 24,
    rds_path: Path | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    raw = load_goal_kicking_games(from_season, to_season, rds_path)
    if raw.empty:
        return pd.DataFrame(), pd.DataFrame()

    raw["player_key"] = raw["player_name"].str.lower().str.strip()
    raw["total_misses"] = raw["shots_at_goal"] - raw["goals"] - raw["behinds"]
    raw = raw[raw["shots_at_goal"] > 0].copy()

    agg = raw.groupby("player_key", as_index=False).agg(
        player_name=("player_name", _mode_value),
        player_id=("player_id", _mode_value),
        team=("team", _mode_team),
        seasons=("season", lambda s: ", ".join(str(y) for y in sorted(s.unique()))),
        games_with_shot=("shots_at_goal", "count"),
        shots_at_goal=("shots_at_goal", "sum"),
        goals=("goals", "sum"),
        behinds=("behinds", "sum"),
        total_misses=("total_misses", "sum"),
        data_sources=("source", lambda s: ", ".join(sorted(s.unique()))),
    )
    agg = agg[agg["shots_at_goal"] >= min_shots].copy()
    agg["goal_accuracy_pct"] = (agg["goals"] / agg["shots_at_goal"] * 100).round(1)
    agg["scoring_shot_pct"] = (
        agg["goals"] / (agg["goals"] + agg["behinds"]).replace(0, pd.NA) * 100
    ).round(1)
    agg["shots_per_game"] = (agg["shots_at_goal"] / agg["games_with_shot"]).round(2)
    agg = agg.sort_values(
        ["goal_accuracy_pct", "goals", "shots_at_goal"],
        ascending=[False, False, False],
    ).reset_index(drop=True)
    agg.insert(0, "rank", agg.index + 1)

    ladder = agg[
        [
            "rank",
            "player_name",
            "player_id",
            "team",
            "seasons",
            "games_with_shot",
            "shots_at_goal",
            "goals",
            "behinds",
            "total_misses",
            "goal_accuracy_pct",
            "scoring_shot_pct",
            "shots_per_game",
            "data_sources",
        ]
    ]
    return ladder, raw


def build_notes_df(
    from_season: int,
    to_season: int,
    min_shots: int,
    games: pd.DataFrame,
) -> pd.DataFrame:
    data_as_at = ""
    if not games.empty and games["match_date"].notna().any():
        latest = pd.to_datetime(games["match_date"], errors="coerce").max()
        if pd.notna(latest):
            data_as_at = latest.date().isoformat()

    season_counts = (
        games.groupby("season")
        .agg(matches=("match_id", "nunique"), player_games=("shots_at_goal", "count"))
        .reset_index()
        if not games.empty
        else pd.DataFrame()
    )
    coverage = (
        "; ".join(
            f"{int(row.season)}: {int(row.matches)} matches"
            for row in season_counts.itertuples()
        )
        if not season_counts.empty
        else "No data loaded."
    )

    return pd.DataFrame(
        {
            "topic": [
                "period",
                "data_as_at",
                "coverage_by_season",
                "minimum_shots",
                "goal_accuracy_pct",
                "scoring_shot_pct",
                "total_misses",
                "oob_on_the_full",
                "sources",
            ],
            "description": [
                f"AFL senior matches aggregated across {from_season}–{to_season} (inclusive).",
                data_as_at or "Unknown",
                coverage,
                f"Players with fewer than {min_shots} shots at goal in the period are excluded.",
                "Goals ÷ shots at goal × 100. Standard AFL shot-at-goal accuracy (GA).",
                "Goals ÷ (goals + behinds) × 100. Accuracy among shots that scored only.",
                "Shots at goal minus goals minus behinds. Non-scoring attempts (post, OOB, etc.).",
                "Not available as a separate stat. total_misses is the closest proxy.",
                "Fryzigg RDS (2012–latest snapshot) for historical seasons; AFL.com public API "
                "(Champion Data) for current-season gaps including partial 2026.",
            ],
        }
    )


def export_goal_kicking_ladder(
    from_season: int = 2022,
    to_season: int = 2024,
    min_shots: int = 24,
    out_dir: Path | None = None,
) -> Path:
    out_dir = out_dir or ROOT / "shared" / "output" / "exports"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"goal_kicking_ladder_{from_season}_{to_season}_min{min_shots}.xlsx"

    ladder, games = build_goal_kicking_ladder_df(from_season, to_season, min_shots)
    notes = build_notes_df(from_season, to_season, min_shots, games)

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        ladder.to_excel(writer, sheet_name="Ladder", index=False)
        notes.to_excel(writer, sheet_name="Notes", index=False)

    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Export goal-kicking accuracy ladder to Excel")
    parser.add_argument("--from-season", type=int, default=2022)
    parser.add_argument("--to-season", type=int, default=2024)
    parser.add_argument("--min-shots", type=int, default=24)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    print(
        export_goal_kicking_ladder(
            args.from_season, args.to_season, args.min_shots, args.out
        )
    )


if __name__ == "__main__":
    main()
