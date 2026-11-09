"""Shared pytest fixtures. Every test gets its own throw-away SQLite database."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import create_app  # noqa: E402


@pytest.fixture
def app(tmp_path):
    return create_app(tmp_path / "test.db")


@pytest.fixture
def client(app):
    return app.test_client()
