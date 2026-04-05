import pytest
from app import create_app

@pytest.fixture
def app():
    app = create_app()
    app.config.update({
        "TESTING": True,
    })
    
    from app.database import db
    from app.models.user import User
    from app.models.url import URL
    from app.models.event import Event
    
    with app.app_context():
        db.create_tables([User, URL, Event], safe=True)
    
    yield app
    
    with app.app_context():
        db.drop_tables([User, URL, Event], safe=True)

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def runner(app):
    return app.test_cli_runner()
