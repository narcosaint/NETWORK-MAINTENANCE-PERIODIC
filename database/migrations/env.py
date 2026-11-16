from alembic import context

from app.config import database_url
from app.database import build_engine
from app.models import Base


def run_migrations_offline():
    context.configure(target_metadata=Base.metadata, url=database_url(), literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    # Integration tests supply a connection scoped to a disposable test schema.
    # Normal CLI/Compose runs continue to build the configured application engine.
    supplied = context.config.attributes.get('connection')
    if supplied is not None:
        context.configure(connection=supplied, target_metadata=Base.metadata)
        with context.begin_transaction():
            context.run_migrations()
        return
    engine = build_engine()
    try:
        with engine.connect() as connection:
            context.configure(connection=connection, target_metadata=Base.metadata)
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
