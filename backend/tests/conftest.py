"""Private-database-free fixtures; all SQLite data is generated outside source."""
import sqlite3
from contextlib import closing

import pytest
from sqlalchemy import event
from app import database
from backend.demo_data import create_legacy_demo
from backend.tools.db_safety import inspect_database, sha256


@pytest.fixture(scope="session")
def legacy_source(tmp_path_factory):
    path = create_legacy_demo(tmp_path_factory.mktemp("fictional-legacy") / "legacy.db")
    before = inspect_database(path)
    checksum = sha256(path)
    assert before["row_count"] == 29
    yield path
    assert sha256(path) == checksum
    assert inspect_database(path) == before


@pytest.fixture(scope="session", autouse=True)
def prohibit_repository_engine_connections():
    def refuse(*args, **kwargs):
        raise AssertionError("Tests must never connect to the default repository database")
    event.listen(database.engine, "do_connect", refuse)
    yield
    event.remove(database.engine, "do_connect", refuse)
