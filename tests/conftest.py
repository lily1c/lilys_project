import pytest
from app import create_app
from app.database import db
from app.models.user import User
from app.models.url import URL
from app.models.event import Event

@pytest.fixture
def app():
    app = create_app()
    app.config.update({
        "TESTING": True,
    })
    
    # Create tables in mock SQLite for testing if needed,
    # or just use the existing DB (if safe).
    # For now, we'll assume the tables exist.
    yield app

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def runner(app):
    return app.test_cli_runner()
