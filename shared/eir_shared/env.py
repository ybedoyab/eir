"""Load the single repo-root .env for backend, agents, and scripts."""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv


def repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").is_file() and (parent / "shared").is_dir():
            return parent
    return here.parents[2]


def load_root_env() -> Path:
    """Load `.env` from the monorepo root. Does not override existing process env."""
    root = repo_root()
    load_dotenv(root / ".env", override=False)
    return root
