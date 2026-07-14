import os

# Set required env vars BEFORE any `app.*` module is imported, since
# get_settings() is cached at import time.
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-not-used")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_bazaarsync.db")
os.environ.setdefault("API_KEY", "")

import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine, init_db
from app.main import app


@pytest.fixture(scope="session", autouse=True)
def _setup_db():
    init_db()
    yield
    Base.metadata.drop_all(bind=engine)
    if os.path.exists("./test_bazaarsync.db"):
        os.remove("./test_bazaarsync.db")


@pytest.fixture
def client():
    return TestClient(app)
