"""
Runtime configuration.

All tuneable values live here so callers never hard-code paths or URLs.
Override any setting with the corresponding environment variable.
"""

from __future__ import annotations

import os
from pathlib import Path

# Load .env from project root if present.  Variables already in the environment
# take precedence (override=False is the default).
try:
    from dotenv import load_dotenv as _load_dotenv

    _load_dotenv(Path(__file__).parent.parent / ".env", override=False)
except ImportError:
    pass

# ── Repository layout ────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"
WORKSHEETS_DIR = OUTPUT_DIR / "worksheets"
SUBMISSIONS_DIR = DATA_DIR / "submissions"
TEMPLATES_DIR = Path(__file__).parent / "templates"

# Create runtime directories if they don't exist yet.
DATA_DIR.mkdir(parents=True, exist_ok=True)
WORKSHEETS_DIR.mkdir(parents=True, exist_ok=True)
SUBMISSIONS_DIR.mkdir(parents=True, exist_ok=True)

# ── Persistence ───────────────────────────────────────────────────────────────
DB_PATH = DATA_DIR / "kumon.db"

# ── Local LLM (OpenAI-compatible endpoint) ────────────────────────────────────
# Constitutional Principle VIII: local-first.
# The LLM runs locally; no data leaves the machine by default.
LLM_BASE_URL: str = os.environ.get("KUMON_LLM_BASE_URL", "http://127.0.0.1:8000/v1")
LLM_MODEL: str = os.environ.get("KUMON_LLM_MODEL", "Qwen3-4B-MLX-4bit")
LLM_API_KEY: str = os.environ.get("KUMON_LLM_API_KEY", "local")  # override with KUMON_LLM_API_KEY
LLM_TIMEOUT: float = float(os.environ.get("KUMON_LLM_TIMEOUT", "30"))
# Max tokens for LLM completion responses.  500 is too small for Qwen3 (thinking tokens
# eat the budget).  Increase via KUMON_LLM_MAX_TOKENS if your model needs more headroom.
LLM_MAX_TOKENS: int = int(os.environ.get("KUMON_LLM_MAX_TOKENS", "1024"))
# Set KUMON_LLM_THINKING=0 to append /no_think to prompts for Qwen3-style models and
# suppress chain-of-thought tokens so the full budget is available for JSON output.
LLM_THINKING_ENABLED: bool = os.environ.get("KUMON_LLM_THINKING", "0") not in {"0", "false", "False"}

# Prompt version — selects the app/prompts/{version}/ directory used for all LLM tasks.
# Set KUMON_PROMPT_VERSION=v1 to revert to the previous prompt set without any code change.
PROMPT_VERSION: str = os.environ.get("KUMON_PROMPT_VERSION", "v2")

# ── Worksheet defaults ────────────────────────────────────────────────────────
DEFAULT_EXERCISE_COUNT: int = int(os.environ.get("KUMON_EXERCISE_COUNT", "15"))
DEFAULT_LOCALE: str = "el-GR"
DEFAULT_LANGUAGE: str = "el"

# ── Default child profile (used when no explicit child is selected) ───────────
DEFAULT_CHILD_ID: str = "default"
DEFAULT_CHILD_NAME: str = os.environ.get("KUMON_CHILD_NAME", "Μαθητής")
DEFAULT_CHILD_AGE: int = int(os.environ.get("KUMON_CHILD_AGE", "10"))
DEFAULT_CHILD_GRADE: int = int(os.environ.get("KUMON_CHILD_GRADE", "4"))


