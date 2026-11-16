from unittest.mock import MagicMock

import pytest
import asyncio
from http_client import ASGIClient
from sqlalchemy.exc import OperationalError

from app.main import app


@pytest.fixture
def client(monkeypatch):
    engine = MagicMock()
    monkeypatch.setattr("app.main.build_engine", lambda: engine)
    lifecycle = app.router.lifespan_context(app)
    asyncio.run(lifecycle.__aenter__())
    yield ASGIClient(app), engine
    asyncio.run(lifecycle.__aexit__(None, None, None))
    engine.dispose.assert_called_once()


def test_liveness_does_not_query_database(client):
    client, engine = client
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    engine.connect.assert_not_called()


def test_database_health_executes_query(client):
    client, engine = client
    response = client.get("/health/db")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    connection = engine.connect.return_value.__enter__.return_value
    assert str(connection.execute.call_args.args[0]) == "SELECT 1"


def test_database_failure_does_not_expose_credentials(client):
    client, engine = client
    engine.connect.side_effect = OperationalError("secret-host", {}, Exception("secret-password"))
    response = client.get("/health/db")
    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}


def test_database_query_failure(client):
    client, engine = client
    engine.connect.return_value.__enter__.return_value.execute.side_effect = OperationalError("SELECT 1", {}, Exception("failure"))
    assert client.get("/health/db").status_code == 503
