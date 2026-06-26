import os
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from db import models
from db.database import Base, get_db
from main import app
from services import llm

# Create an in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def mock_llm_extraction(monkeypatch):
    """
    Mock the Gemini API call to return deterministic dummy data
    so we don't hit the real API or use quota during tests.
    """

    def dummy_extract(text):
        return {
            "summary": "Experienced software engineer with a proven track record.",
            "experience_years": 5,
            "education": "B.S. Computer Science",
            "past_titles": ["Software Developer", "Senior Engineer"],
        }

    monkeypatch.setattr(llm, "extract_advanced_info", dummy_extract)


@pytest.fixture(autouse=True)
def clean_db():
    """Ensure the database is clean before each test"""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
