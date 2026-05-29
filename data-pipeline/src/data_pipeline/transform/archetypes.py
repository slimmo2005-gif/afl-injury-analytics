"""Map Fryzigg position codes to broad positional archetypes."""

from __future__ import annotations

POSITION_TO_ARCHETYPE: dict[str, str] = {
    # Key defender
    "FB": "key_defender",
    "CHB": "key_defender",
    "HBFL": "key_defender",
    "HBFR": "key_defender",
    "BPL": "key_defender",
    "BPR": "key_defender",
    # Key forward
    "FF": "key_forward",
    "CHF": "key_forward",
    "FPL": "key_forward",
    "FPR": "key_forward",
    # Inside mid
    "C": "inside_mid",
    "RR": "inside_mid",
    "WR": "inside_mid",
    "R": "inside_mid",
    # Outside mid
    "WL": "outside_mid",
    "W": "outside_mid",
    # Ruck
    "RK": "ruck",
    # Pressure / half-forward
    "HFFL": "pressure_forward",
    "HFFR": "pressure_forward",
    "HF": "pressure_forward",
    # Utility / interchange
    "INT": "utility",
    "SUB": "utility",
    "I/C": "utility",
}

ARCHETYPE_LABELS: dict[str, str] = {
    "key_defender": "Key Defender",
    "key_forward": "Key Forward",
    "inside_mid": "Inside Mid",
    "outside_mid": "Outside Mid",
    "ruck": "Ruck",
    "pressure_forward": "Pressure Forward",
    "utility": "Utility",
}


def map_position(position: str | None) -> str:
    if not position or (isinstance(position, float) and str(position) == "nan"):
        return "utility"
    code = str(position).strip().upper()
    return POSITION_TO_ARCHETYPE.get(code, "utility")
