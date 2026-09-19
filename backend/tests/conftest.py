import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app import database
from app.database import Base, get_db
from app.config import settings
from app.celery_app import celery_app

# Tests run Celery tasks synchronously in-process - no broker/worker needed.
# task_store_eager_result is required too: without it, eager mode runs the
# task but doesn't persist its result to the backend, so a fresh
# AsyncResult(task_id) lookup (i.e. the polling endpoint, a separate object
# from the one .delay() returned) finds nothing.
celery_app.conf.update(task_always_eager=True, task_eager_propagates=True, task_store_eager_result=True)

engine = create_engine(settings.TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Celery tasks (app/tasks/*) call database.SessionLocal() directly rather
# than going through FastAPI's Depends(get_db) - overriding the module
# attribute here (not just get_db below) makes eager-mode tasks in tests
# see the same test database as the request that enqueued them.
database.SessionLocal = TestingSessionLocal


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_test_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db_session():
    """A direct DB session for tests that need to assert on rows the API
    doesn't expose through any endpoint (e.g. AuditLog)."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
