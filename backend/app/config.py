"""Runtime configuration loaded from the project-level .env file."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
# Backup provider, used automatically when the OpenAI key is expired/invalid, out of quota, or OpenAI is down.
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5")
LLM_PROVIDERS = [p.strip() for p in os.getenv("LLM_PROVIDERS", "openai,anthropic").split(",") if p.strip()]  # failover order
MAIN_DB_URL = os.getenv("MAIN_DB_URL", "postgresql+psycopg://lng:lng@localhost:5433/lng_main")
EXTERNAL_DB_URL = os.getenv("EXTERNAL_DB_URL", "postgresql+psycopg://lng:lng@localhost:5433/lng_external")
TRAIN_CSV = ROOT_DIR / os.getenv("TRAIN_CSV", "LNG_market_training_2024_2025.csv")
EVAL_CSV = ROOT_DIR / os.getenv("EVAL_CSV", "LNG_market_evaluation_blintest model_2026_Jan_Feb.csv")
REPORTS_DIR = ROOT_DIR / "reports"

TARGET = "JKM_Historical"
EXOG = ["HH_Historical", "Brent_price", "US_Index_Historical", "Gold_Historical"]

# Security guardrails (see app/guardrails.py and README "Bảo mật")
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5177").split(",") if o.strip()]
API_TOKEN = os.getenv("API_TOKEN", "").strip()  # empty => no auth (local dev only)
RATE_LIMIT_PER_MIN = int(os.getenv("RATE_LIMIT_PER_MIN", "10"))  # POST requests per client IP
MAX_ACTIVE_RUNS = int(os.getenv("MAX_ACTIVE_RUNS", "3"))
