
import pytest
from backend import create_app
from backend.extensions import db as _db
from config import DevelopmentConfig

class TestConfig(DevelopmentConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"  # Use in-memory DB for tests
    WTF_CSRF_ENABLED = False  # Disable CSRF for easier API testing

@pytest.fixture(scope="session")
def app():
    """Create and configure a new app instance for each test session."""
    app = create_app(TestConfig)
    return app

@pytest.fixture(scope="function")
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture(scope="function")
def db(app):
    """Setup and teardown a clean database for each test function."""
    with app.app_context():
        _db.create_all()
        yield _db
        _db.drop_all()
