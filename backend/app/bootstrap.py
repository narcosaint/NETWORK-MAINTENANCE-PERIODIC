"""Explicit operator command to create the first supervisor, without default credentials."""
from getpass import getpass
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import build_engine
from app.models import User
from app.schemas import UserCreate
from app.security import hash_password


def main():
    data = UserCreate(username=input('Username: '), name=input('Name: '),
                      password=getpass('Password (12+ characters): '), role='supervisor')
    engine = build_engine()
    try:
        with Session(engine) as session, session.begin():
            # Serializes concurrent bootstrap attempts on PostgreSQL.
            from sqlalchemy import text
            session.execute(text('LOCK TABLE users IN EXCLUSIVE MODE'))
            if session.scalar(select(User.id).limit(1)):
                raise SystemExit('Bootstrap refused: users already exist. Use supervisor API.')
            session.add(User(username=data.username, name=data.name, role=data.role,
                             active=True, password_hash=hash_password(data.password)))
    finally:
        engine.dispose()


if __name__ == '__main__':
    main()
