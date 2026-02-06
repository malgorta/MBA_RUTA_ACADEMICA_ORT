"""Root conftest.py to initialize DB before any test module imports models."""
import os
import pytest

# Set in-memory DB BEFORE any test module imports lib.db
os.environ.setdefault('DB_PATH', ':memory:')


@pytest.fixture(autouse=True, scope='session')
def init_test_db():
    """Initialize test database schema before any tests run."""
    from lib.db import init_db, get_engine, get_sessionmaker
    from sqlalchemy import inspect
    
    # Clear any cached engine/sessionmaker to ensure fresh DB connection
    get_engine.cache_clear()
    get_sessionmaker.cache_clear()
    
    # Initialize schema
    init_db()
    
    # Verify schema was created
    engine = get_engine()
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"\nInitialized test DB with tables: {tables}")
    
    yield
