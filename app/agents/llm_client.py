"""
Local LLM client — OpenAI-compatible endpoint.

Constitutional Principle VIII — Local-First Architecture:
  The LLM runs at http://127.0.0.1:8000/v1 (configurable via KUMON_LLM_BASE_URL).
  No data leaves the local machine unless the operator explicitly points
  KUMON_LLM_BASE_URL at a remote service.

Constitutional Principle I — Deterministic Before Agentic:
  This client is used ONLY for tasks that genuinely benefit from language
  understanding: explanations, summaries, and narrative generation.
  It is NEVER used for arithmetic evaluation or progression decisions.

Usage
-----
  from app.agents.llm_client import get_llm_client
  client = get_llm_client()
  response = client.chat.completions.create(
      model=cfg.LLM_MODEL,
      messages=[{"role": "user", "content": "..."}],
  )
"""

from __future__ import annotations

from functools import lru_cache

from openai import OpenAI

import app.config as cfg


@lru_cache(maxsize=1)
def get_llm_client() -> OpenAI:
    """
    Return a cached OpenAI client pointed at the local LLM endpoint.

    The first call initialises the client; subsequent calls return the same
    instance.  Thread-safe for read-only use.
    """
    return OpenAI(
        base_url=cfg.LLM_BASE_URL,
        api_key=cfg.LLM_API_KEY,
        timeout=cfg.LLM_TIMEOUT,
    )



def is_llm_available() -> bool:
    """
    Quick health-check: returns True if the local LLM endpoint responds.

    Used by the CLI to warn the parent when the LLM is offline (the core
    worksheet workflow still works without it).
    """
    try:
        client = get_llm_client()
        models = client.models.list()
        return len(models.data) > 0
    except Exception:
        return False

