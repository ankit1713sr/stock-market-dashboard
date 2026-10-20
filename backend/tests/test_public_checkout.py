"""A public checkout works from fictional inputs, without any shipped database."""
import os
import sqlite3
import subprocess
import sys
from contextlib import closing
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker

from app import database, main
from backend.demo_data import fictional_trades, create_legacy_demo
from backend.tools.create_demo_database import create_demo_database
from backend.tools.db_safety import inspect_database, sha256
from backend.migrations.runner import migration_plan


def test_fixture_has_legacy_edge_cases_without_real_symbols(legacy_source):
    rows = fictional_trades()
    assert len(rows) == 29 and [r["id"] for r in rows] == list(range(1, 30))
    assert all(r["symbol"].startswith("SIM") and "FICTIONAL" in r["notes"] for r in rows)
    assert sum(r["asset"] == "Futures" for r in rows) == 4
    assert rows[0]["asset"] is None and any(r["qty"] % 1 for r in rows)
    assert any((r["side"] == "BUY" and r["stop_loss"] >= r["entry_price"]) or
               (r["side"] == "SELL" and r["stop_loss"] <= r["entry_price"]) for r in rows)


def test_fictional_database_generation_is_byte_repeatable_and_nonoverwriting(tmp_path):
    a = create_legacy_demo(tmp_path / "a.db")
    b = create_legacy_demo(tmp_path / "b.db")
    assert sha256(a) == sha256(b)
    with pytest.raises(FileExistsError):
        create_legacy_demo(a)


def test_demo_initialization_migrates_new_path_and_api_can_read_it(tmp_path, monkeypatch):
    path, backup = tmp_path / "demo.db", tmp_path / "baseline.db"
    result = create_demo_database(path, backup)
    assert result["pending"] == []
    assert migration_plan(path)["applied"] == ["001_legacy_baseline", "002_trade_cost_accounting"]
    assert inspect_database(path)["row_count"] == 29
    assert inspect_database(backup)["row_count"] == 29
    engine = create_engine(URL.create("sqlite", database=str(path)), connect_args={"check_same_thread":False})
    sessions = sessionmaker(bind=engine)
    monkeypatch.setattr(database, "SessionLocal", sessions)
    try:
        with TestClient(main.app) as client:
            assert client.get("/health").json()["trades_count"] == 29
            trades = client.get("/api/v1/trades").json()
            assert len(trades) == 29 and all(t["symbol"].startswith("SIM") for t in trades)
            assert all(t["net_pnl"] is None for t in trades)
    finally:
        engine.dispose()


@pytest.mark.parametrize("occupied", ["database", "backup"])
def test_demo_initialization_refuses_existing_paths_before_writing(tmp_path, occupied):
    path, backup = tmp_path / "demo.db", tmp_path / "baseline.db"
    target = path if occupied == "database" else backup
    target.write_bytes(b"retain")
    with pytest.raises(FileExistsError):
        create_demo_database(path, backup)
    assert target.read_bytes() == b"retain"
    assert not (backup if occupied == "database" else path).exists()


def test_missing_database_returns_503_and_is_not_created(tmp_path, monkeypatch):
    missing = tmp_path / "missing.db"
    url = URL.create("sqlite", database=missing.as_uri()+"?mode=rw", query={"uri":"true"})
    engine = create_engine(url)
    monkeypatch.setattr(database, "SessionLocal", sessionmaker(bind=engine))
    try:
        with TestClient(main.app) as client:
            response = client.get("/health")
            assert response.status_code == 503 and "not initialized" in response.text
        assert not missing.exists()
    finally:
        engine.dispose()


def test_demo_cli_runs_without_backend_pythonpath_or_existing_database(tmp_path):
    root = Path(__file__).resolve().parents[2]
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    environment.pop("TRADEPULSE_DB_PATH", None)
    result = subprocess.run([sys.executable, "-B", "-m", "backend.tools.create_demo_database",
                             str(tmp_path / "cli.db"), "--backup", str(tmp_path / "cli-backup.db")],
                            cwd=root, env=environment, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert inspect_database(tmp_path / "cli.db")["row_count"] == 29
