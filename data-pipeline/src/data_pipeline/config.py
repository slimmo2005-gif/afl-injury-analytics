from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PIPELINE_ROOT = ROOT / "data-pipeline"
RAW_DIR = PIPELINE_ROOT / "raw"
DB_PATH = PIPELINE_ROOT / "processed" / "afl_analytics.duckdb"
SHARED_OUTPUT = ROOT / "shared" / "output"
FRONTEND_DATA = ROOT / "frontend" / "public" / "data"

MIN_SEASON = 2012
DEFAULT_SEASON = 2025
SQUIGGLE_BASE = "https://api.squiggle.com.au"
FRYZIGG_RDS_URL = "http://www.fryziggafl.net/static/fryziggafl.rds"
FRYZIGG_RDS_FILE = RAW_DIR / "fryziggafl.rds"

TEAM_ALIASES: dict[str, str] = {
    "Brisbane": "Brisbane Lions",
    "Footscray": "Western Bulldogs",
    "GWS": "Greater Western Sydney",
    "GWS GIANTS": "Greater Western Sydney",
    "Greater Western Sydney Giants": "Greater Western Sydney",
}
