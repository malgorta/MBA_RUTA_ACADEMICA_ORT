import os
import pytest

# Ensure tests use an in-memory database before any test module imports lib.db
os.environ.setdefault('DB_PATH', ':memory:')


@pytest.fixture(autouse=True, scope='session')
def ensure_clean_db():
    # Import models so that Base.metadata is populated before creating tables
    import importlib
    importlib.import_module('lib.models')
    from lib.db import init_db
    init_db()
    yield
