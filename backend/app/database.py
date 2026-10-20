from pathlib import Path
from fastapi import HTTPException
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import URL
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, sessionmaker
import os

# Preserve the historical default; explicit separate DB paths support safe cutover.
_HERE = os.path.dirname(os.path.abspath(__file__))
_REPOSITORY_DB = Path(_HERE).parent / "tradepulse.db"
_DB_PATH = Path(os.environ.get("TRADEPULSE_DB_PATH", str(_REPOSITORY_DB))).resolve()
# The repository DB remains read-only even if explicitly selected via env.
_is_repository = _DB_PATH == _REPOSITORY_DB.resolve() or (
    _DB_PATH.exists() and _REPOSITORY_DB.exists() and _DB_PATH.samefile(_REPOSITORY_DB)
)
_mode = "ro" if _is_repository else "rw"  # never silently create a missing DB
SQLALCHEMY_DATABASE_URL = URL.create(
    "sqlite", database=_DB_PATH.as_uri() + f"?mode={_mode}", query={"uri": "true"}
)

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# SQLAlchemy 2.x declarative base (replaces deprecated ext.declarative)
class Base(DeclarativeBase):
    pass


def get_db():
    """Dependency: yields a DB session and closes it when the request is done."""
    db = SessionLocal()
    try:
        # Inspection only: explain pending migrations before ORM selects new columns.
        from migrations.revisions import ACCOUNTING_COLUMNS
        try:
            columns = {c["name"] for c in inspect(db.get_bind()).get_columns("trades")}
        except SQLAlchemyError as error:
            raise HTTPException(503, "Database unavailable or not initialized; select a migrated database via TRADEPULSE_DB_PATH") from error
        if not set(ACCOUNTING_COLUMNS) <= columns:
            raise HTTPException(503, "Accounting schema pending; migrate a verified separate copy explicitly")
        yield db
    finally:
        db.close()
