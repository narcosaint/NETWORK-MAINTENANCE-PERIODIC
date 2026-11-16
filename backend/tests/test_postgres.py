"""Read-only integration check against an explicitly supplied test database."""
import os

import pytest
from sqlalchemy import create_engine, text


@pytest.mark.skipif(not os.environ.get("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL is not set")
def test_real_postgresql_connection():
    engine = create_engine(os.environ["TEST_DATABASE_URL"], connect_args={"connect_timeout": 3})
    try:
        assert engine.dialect.name == "postgresql"
        with engine.connect() as connection:
            assert connection.execute(text("SELECT 1")).scalar_one() == 1
    finally:
        engine.dispose()
