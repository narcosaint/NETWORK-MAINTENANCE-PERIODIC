import os

from sqlalchemy import URL


def database_url() -> URL:
    password = os.environ.get("POSTGRES_PASSWORD")
    if not password:
        raise RuntimeError("POSTGRES_PASSWORD must be set")
    return URL.create(
        "postgresql+psycopg",
        username=os.environ.get("POSTGRES_USER", "hotel_maintenance"),
        password=password,
        host=os.environ.get("POSTGRES_HOST", "db"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        database=os.environ.get("POSTGRES_DB", "hotel_maintenance"),
    )
