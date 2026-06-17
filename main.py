"""
Kumon Agent — entry point for direct execution.

For the CLI, use:
  uv run kumon --help

For the web API (Milestone 2+):
  uv run uvicorn app.api:api --reload

This file exists for convenience (python main.py) and as a development
quick-start.
"""

from app.cli.main import app

if __name__ == "__main__":
    app()
