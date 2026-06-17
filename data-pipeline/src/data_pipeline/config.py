from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PIPELINE_ROOT = ROOT / "data-pipeline"
RAW_DIR = PIPELINE_ROOT / "raw"
DB_PATH = PIPELINE_ROOT / "processed" / "afl_analytics.duckdb"
SHARED_OUTPUT = ROOT / "shared" / "output"
FRONTEND_DATA = ROOT / "frontend" / "public" / "data"

MIN_SEASON = 2012
DEFAULT_SEASON = 2025
CURRENT_SEASON = 2026
HISTORICAL_MAX_SEASON = 2025
SQUIGGLE_BASE = "https://api.squiggle.com.au"
FRYZIGG_RDS_URL = "http://www.fryziggafl.net/static/fryziggafl.rds"
FRYZIGG_RDS_FILE = RAW_DIR / "fryziggafl.rds"

TEAM_ALIASES: dict[str, str] = {
    "Adelaide Crows": "Adelaide",
    "Brisbane": "Brisbane Lions",
    "Footscray": "Western Bulldogs",
    "Geelong Cats": "Geelong",
    "Gold Coast Suns": "Gold Coast",
    "Gold Coast SUNS": "Gold Coast",
    "GWS": "Greater Western Sydney",
    "GWS GIANTS": "Greater Western Sydney",
    "GWS Giants": "Greater Western Sydney",
    "Greater Western Sydney Giants": "Greater Western Sydney",
    "Sydney Swans": "Sydney",
    "West Coast Eagles": "West Coast",
}

# BigFooty forum threads with full-club injury tables (slug after /threads/).
BIGFOOTY_FORUM_THREADS: dict[int, str] = {
    2024: "injury-list-afl-2024-updated-every-few-days.1377977",
    2025: "afl-injury-lists-2025-updated-regularly-all-links-to-news-welcome.1393192",
    2026: "afl-injury-lists-2026-updated-a-couple-of-times-a-week.1406206",
}

BIGFOOTY_INJURIES_CATEGORY = "https://www.bigfooty.com/category/afl-injuries/"
WAYBACK_INJURY_URL = "https://www.afl.com.au/matches/injury-list"
WAYBACK_CDX_CACHE = RAW_DIR / "wayback_injury_cdx.json"
