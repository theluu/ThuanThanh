"""Runtime configuration loaded from the project-level .env file."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
MAIN_DB_URL = os.getenv("MAIN_DB_URL", "postgresql+psycopg://lng:lng@localhost:5433/lng_main")
EXTERNAL_DB_URL = os.getenv("EXTERNAL_DB_URL", "postgresql+psycopg://lng:lng@localhost:5433/lng_external")
TRAIN_CSV = ROOT_DIR / os.getenv("TRAIN_CSV", "LNG_market_training_2024_2025.csv")
EVAL_CSV = ROOT_DIR / os.getenv("EVAL_CSV", "LNG_market_evaluation_blintest model_2026_Jan_Feb.csv")
REPORTS_DIR = ROOT_DIR / "reports"

TARGET = "JKM_Historical"
EXOG = ["HH_Historical", "Brent_price", "US_Index_Historical", "Gold_Historical"]
