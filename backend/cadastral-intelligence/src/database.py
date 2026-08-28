from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from .config import settings


engine: Engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
)


def fetch_one(query: str, params: dict | None = None):
    with engine.begin() as connection:
        result = connection.execute(
            text(query),
            params or {}
        )
        return result.mappings().first()


def fetch_all(query: str, params: dict | None = None):
    with engine.begin() as connection:
        result = connection.execute(
            text(query),
            params or {}
        )
        return result.mappings().all()


def execute(query: str, params: dict | None = None):
    with engine.begin() as connection:
        connection.execute(
            text(query),
            params or {}
        )