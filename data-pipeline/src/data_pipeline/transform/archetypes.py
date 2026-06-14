"""Map Fryzigg position codes to broad positional archetypes."""

from __future__ import annotations

import pandas as pd

MID_ARCHETYPES = frozenset({"inside_mid", "outside_mid"})

POSITION_TO_ARCHETYPE: dict[str, str] = {
    "FB": "key_defender",
    "CHB": "key_defender",
    "BPL": "key_defender",
    "BPR": "key_defender",
    "HBFL": "outside_mid",
    "HBFR": "outside_mid",
    "FF": "key_forward",
    "CHF": "key_forward",
    "FPL": "key_forward",
    "FPR": "key_forward",
    "C": "inside_mid",
    "RR": "inside_mid",
    "WR": "inside_mid",
    "R": "inside_mid",
    "WL": "outside_mid",
    "W": "outside_mid",
    "RK": "ruck",
    "HFFL": "pressure_forward",
    "HFFR": "pressure_forward",
    "HF": "pressure_forward",
    "INT": "utility",
    "SUB": "utility",
    "I/C": "utility",
}

ARCHETYPE_LABELS: dict[str, str] = {
    "key_defender": "Key Defender",
    "rebound_defender": "Rebound Defender",
    "key_forward": "Key Forward",
    "inside_mid": "Inside Mid",
    "outside_mid": "Outside Mid",
    "ruck": "Ruck",
    "pressure_forward": "Pressure Forward",
    "utility": "Utility",
}


def map_position(position: str | None) -> str:
    if not position or (isinstance(position, float) and pd.isna(position)):
        return "utility"
    code = str(position).strip().upper()
    return POSITION_TO_ARCHETYPE.get(code, "utility")


def infer_archetype_from_stats(
    *,
    disposals_pg: float = 0,
    goals_pg: float = 0,
    score_inv_pg: float = 0,
    clearances_pg: float = 0,
    intercepts_pg: float = 0,
    hitouts_pg: float = 0,
    tackles_pg: float = 0,
    contested_marks_pg: float = 0,
    metres_per100_pg: float = 0,
) -> str:
    """
    Classify from season stats. Defender/forward rules are custom; mids use
    the original clearance/disposal thresholds (unchanged from first stat model).
    """
    if hitouts_pg >= 6 or (hitouts_pg >= 3 and hitouts_pg > clearances_pg * 1.5):
        return "ruck"

    # --- defenders (updated rules) ---
    if intercepts_pg >= 4.0 and contested_marks_pg >= 0.5 and goals_pg < 0.5:
        return "key_defender"

    # --- mids (original rules — before forward/defender overlap) ---
    if clearances_pg >= 4.0 or (clearances_pg >= 3.0 and disposals_pg >= 18):
        return "inside_mid"

    if disposals_pg >= 20 and clearances_pg < 3.5 and goals_pg < 0.4:
        return "outside_mid"

    if clearances_pg < 2.5 and goals_pg < 0.4 and contested_marks_pg < 0.45:
        if metres_per100_pg >= 3.0:
            return "rebound_defender"
        if metres_per100_pg >= 2.3 and intercepts_pg >= 3.0 and contested_marks_pg < 0.2:
            return "rebound_defender"

    if (
        intercepts_pg >= 2.0
        and contested_marks_pg >= 0.55
        and goals_pg < 0.45
        and metres_per100_pg < 3.0
    ):
        return "key_defender"

    # --- forwards (updated rules) ---
    if contested_marks_pg >= 0.9 and goals_pg >= 0.45:
        return "key_forward"
    if goals_pg >= 0.85 and contested_marks_pg >= 0.55:
        return "key_forward"
    if goals_pg >= 1.3 and contested_marks_pg >= 0.35:
        return "key_forward"

    if (
        clearances_pg < 2.5
        and contested_marks_pg < 0.45
        and (goals_pg >= 0.25 or score_inv_pg >= 3.0)
        and (tackles_pg >= 2.5 or (tackles_pg >= 2.0 and score_inv_pg >= 4.5))
    ):
        return "pressure_forward"

    return "utility"


def resolve_archetype(
    fryzigg_mode_position: str | None,
    *,
    disposals_pg: float = 0,
    goals_pg: float = 0,
    score_inv_pg: float = 0,
    clearances_pg: float = 0,
    intercepts_pg: float = 0,
    hitouts_pg: float = 0,
    tackles_pg: float = 0,
    contested_marks_pg: float = 0,
    metres_per100_pg: float = 0,
) -> tuple[str, str, str]:
    """
    Returns (final_archetype, stat_archetype, fryzigg_archetype).
    Fryzigg mode fills in inside/outside mid only when stats are ambiguous.
    """
    stat_arch = infer_archetype_from_stats(
        disposals_pg=disposals_pg,
        goals_pg=goals_pg,
        score_inv_pg=score_inv_pg,
        clearances_pg=clearances_pg,
        intercepts_pg=intercepts_pg,
        hitouts_pg=hitouts_pg,
        tackles_pg=tackles_pg,
        contested_marks_pg=contested_marks_pg,
        metres_per100_pg=metres_per100_pg,
    )
    fryzigg_arch = map_position(fryzigg_mode_position)

    if stat_arch != "utility":
        return stat_arch, stat_arch, fryzigg_arch

    if fryzigg_arch in MID_ARCHETYPES:
        return fryzigg_arch, stat_arch, fryzigg_arch

    return "utility", stat_arch, fryzigg_arch
