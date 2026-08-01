"""Central configuration — paths, API credentials, and pipeline constants."""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent

load_dotenv(BASE_DIR / ".env")

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "app.db"
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", str(Path.home() / "Desktop" / "output")))

# MOCK_LLM=1 replaces every model call with canned fixtures (free, deterministic demos)
MOCK_LLM = os.getenv("MOCK_LLM", "0") == "1"
# The app's own address — used by the optional vision audit to screenshot a build's
# live preview. Override if you run uvicorn on a different port.
SELF_URL = os.getenv("SELF_URL", "http://localhost:8000")
# DEV_ROUTES=1 mounts /api/dev/* helpers (seed-brief); on by default for a student project
DEV_ROUTES = os.getenv("DEV_ROUTES", "1") == "1"

LLM_TIMEOUT_S = 120          # read timeout — AsyncOpenAI can otherwise hang ~600s
RECHECK_TIMEOUT_S = 300      # recheck reads the whole site — slow models need longer
AUDIT_TIMEOUT_S = 240        # audit also reads every file
LLM_MAX_RETRIES = 4          # retries on 429 / timeout / 5xx, exponential jitter
MAX_CONTINUATIONS = 3        # continuation calls when finish_reason == "length"
PAGE_CONCURRENCY = 5         # semaphore around parallel page builds
MAX_PAGES = 5

INTERVIEWER_MAX_TOKENS = 1200
SPEC_MAX_TOKENS = 8000       # copywriter / designer JSON specs
CSS_MAX_TOKENS = 10000
PAGE_MAX_TOKENS = 8000
JS_MAX_TOKENS = 6000
RECHECK_MAX_TOKENS = 16000
AUDIT_MAX_TOKENS = 4000
