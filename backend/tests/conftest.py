import os
import sys
import tempfile
import pytest

# Ensure backend directory is in python path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Use SQLite for tests
test_db_file = os.path.join(tempfile.gettempdir(), "test_stream_worker.db")
os.environ["DATABASE_URL"] = f"sqlite:///{test_db_file}"
os.environ["LEDGER_FILE"] = os.path.join(tempfile.gettempdir(), "test_ledger.txt")

import fakeredis
from app.db import Base, engine, SessionLocal
from app.stream_worker import init_stream_group, STREAM_KEY, CONSUMER_GROUP


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    if os.path.exists(test_db_file):
        try:
            os.remove(test_db_file)
        except OSError:
            pass


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def fake_redis():
    r = fakeredis.FakeRedis(decode_responses=True)
    init_stream_group(r)
    return r
