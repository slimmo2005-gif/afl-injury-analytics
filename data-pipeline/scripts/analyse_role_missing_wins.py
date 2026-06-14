"""Analyse how missing players by archetype correlates with winning (multi-season)."""

from __future__ import annotations

import duckdb

from data_pipeline.config import DB_PATH
from data_pipeline.export.core22_impact import build_core22_impact_bundle


def main() -> None:
    con = duckdb.connect(str(DB_PATH), read_only=True)
    bundle = build_core22_impact_bundle(con)
    con.close()

    for method in bundle["methods"]:
        print(f"\n{'=' * 72}")
        print(f"  {method['label']}")
        print(f"{'=' * 72}")
        print(f"Team-rounds: {method['teamRounds']}, avg missed PVS: {method['avgMissedPvs']}")
        print("\nTop correlations:")
        for row in method["correlations"][:6]:
            print(f"  {row['role']:20} win={row['corrWin']:+.3f}")
        print("\nStar miss (worst):")
        for row in method["starMiss"][:4]:
            print(f"  {row['role']:20} {row['deltaPp']:+.1f} pp")


if __name__ == "__main__":
    main()
