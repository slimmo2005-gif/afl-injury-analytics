"""Apply documented manual corrections to availability rows after VFL integration."""

from __future__ import annotations

import json
from pathlib import Path

import duckdb

from ..config import PIPELINE_ROOT

ADJUSTMENTS_PATH = PIPELINE_ROOT / "data" / "availability_adjustments.json"
DISPLAY_LABELS_PATH = PIPELINE_ROOT / "data" / "injury_display_labels.json"


def _load_json_list(path: Path) -> list[dict]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        return list(data.get("adjustments", []))
    return list(data)


def load_availability_adjustments(path: Path | None = None) -> list[dict]:
    """All adjustment records (row + display) for label lookup."""
    path = path or ADJUSTMENTS_PATH
    rows = _load_json_list(path)
    display = _load_json_list(DISPLAY_LABELS_PATH)
    return rows + display


def load_row_adjustments() -> list[dict]:
    """Adjustments that mutate availability rows (not display-only labels)."""
    row_keys = {
        "exclude_rounds_before",
        "exclude_rounds_after",
        "exclude_rounds",
        "vfl_only_rounds",
        "vfl_only_round_range",
        "set_status",
    }
    combined = _load_json_list(ADJUSTMENTS_PATH) + _load_json_list(DISPLAY_LABELS_PATH)
    return [adj for adj in combined if any(k in adj for k in row_keys)]


def adjustment_key_injuries_index(path: Path | None = None) -> dict[tuple[str, str, int], list[str]]:
    """Lookup manual injury labels for frontend display (player_id, team, season)."""
    index: dict[tuple[str, str, int], list[str]] = {}
    for adj in load_availability_adjustments(path):
        labels = adj.get("key_injuries")
        player_id = adj.get("player_id")
        team = adj.get("team")
        season = adj.get("season")
        if not labels or not player_id or not team or season is None:
            continue
        index[(str(player_id), str(team), int(season))] = [str(x) for x in labels]
    return index


def apply_availability_adjustments(
    con: duckdb.DuckDBPyConnection,
    path: Path | None = None,
) -> int:
    """Delete or relabel availability rows per availability_adjustments.json."""
    adjustments = load_row_adjustments()
    if not adjustments:
        return 0

    changed = 0
    for adj in adjustments:
        player_id = adj.get("player_id")
        team = adj.get("team")
        season = adj.get("season")
        if not player_id or not team or season is None:
            continue

        before = adj.get("exclude_rounds_before")
        if before is not None:
            con.execute(
                """
                DELETE FROM availability
                WHERE player_id = ?
                  AND team = ?
                  AND season = ?
                  AND round < ?
                """,
                [player_id, team, int(season), int(before)],
            )
            changed += 1
            print(
                f"[adjustments] {adj.get('player_name', player_id)} "
                f"{team} {season}: exclude rounds before {before}"
            )

        after = adj.get("exclude_rounds_after")
        if after is not None:
            con.execute(
                """
                DELETE FROM availability
                WHERE player_id = ?
                  AND team = ?
                  AND season = ?
                  AND round > ?
                """,
                [player_id, team, int(season), int(after)],
            )
            changed += 1
            print(
                f"[adjustments] {adj.get('player_name', player_id)} "
                f"{team} {season}: exclude rounds after {after}"
            )

        for rnd in adj.get("exclude_rounds", []):
            con.execute(
                """
                DELETE FROM availability
                WHERE player_id = ? AND team = ? AND season = ? AND round = ?
                """,
                [player_id, team, int(season), int(rnd)],
            )
            changed += 1

        for rnd in adj.get("vfl_only_rounds", []):
            con.execute(
                """
                UPDATE availability
                SET status = 'vfl_only', vfl_played = TRUE
                WHERE player_id = ?
                  AND team = ?
                  AND season = ?
                  AND round = ?
                  AND NOT afl_played
                """,
                [player_id, team, int(season), int(rnd)],
            )
            changed += 1

        vfl_range = adj.get("vfl_only_round_range")
        if vfl_range:
            lo, hi = int(vfl_range["from"]), int(vfl_range["to"])
            con.execute(
                """
                UPDATE availability
                SET status = 'vfl_only', vfl_played = TRUE
                WHERE player_id = ?
                  AND team = ?
                  AND season = ?
                  AND round BETWEEN ? AND ?
                  AND NOT afl_played
                """,
                [player_id, team, int(season), lo, hi],
            )
            changed += 1

        relabel = adj.get("set_status") or {}
        for rnd_str, status in relabel.items():
            con.execute(
                """
                UPDATE availability
                SET status = ?
                WHERE player_id = ? AND team = ? AND season = ? AND round = ?
                """,
                [status, player_id, team, int(season), int(rnd_str)],
            )
            changed += 1

    return changed
