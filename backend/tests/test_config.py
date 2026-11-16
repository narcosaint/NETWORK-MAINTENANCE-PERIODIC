import pytest
from app.config import database_url


def test_password_required(monkeypatch):
    monkeypatch.delenv("POSTGRES_PASSWORD", raising=False)
    with pytest.raises(RuntimeError, match="POSTGRES_PASSWORD"):
        database_url()


def test_special_characters_in_password(monkeypatch):
    monkeypatch.setenv("POSTGRES_PASSWORD", "test@:/%password")
    url = database_url()
    assert url.password == "test@:/%password"
    assert "test@:/%password" not in str(url)
