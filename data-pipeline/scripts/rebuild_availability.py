"""Rebuild availability + downstream tables without re-ingesting sources."""

from __future__ import annotations

from data_pipeline.db import connect
from data_pipeline.export.frontend import write_metrics
from data_pipeline.pipeline import _apply_vfl_layer
from data_pipeline.transform.absences import enrich_absence_reasons
from data_pipeline.transform.availability import build_availability
from data_pipeline.transform.availability_adjustments import apply_availability_adjustments
from data_pipeline.transform.continuity import build_archetype_continuity
from data_pipeline.transform.pvs import build_player_profiles, build_player_value
from data_pipeline.transform.unavailability import build_team_round_value, enrich_availability_status


def main() -> None:
    con = connect()
    print("[rebuild] availability …")
    build_availability(con)
    _apply_vfl_layer(con)
    apply_availability_adjustments(con)
    enrich_availability_status(con)
    enrich_absence_reasons(con)
    build_player_profiles(con)
    build_player_value(con)
    build_team_round_value(con)
    build_archetype_continuity(con)
    path = write_metrics(con)
    print(f"[rebuild] exported -> {path}")


if __name__ == "__main__":
    main()
