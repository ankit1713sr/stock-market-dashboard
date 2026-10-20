"""Every write targets pytest's disposable directory, never the source DB."""
import json
import sqlite3
from pathlib import Path
import pytest

from backend.tools.db_safety import (
    REPOSITORY_DATABASE, backup_database, inspect_database, manifest_path,
    restore_backup, sha256, verify_backup,
)
from backend.migrations.runner import migration_plan, upgrade
from backend.migrations.revisions import ACCOUNTING_COLUMNS


@pytest.fixture
def legacy_copy(tmp_path, legacy_source):
    destination = tmp_path / "legacy.db"
    backup_database(legacy_source, destination)
    return destination


def test_verified_backup_restore_to_new_path_preserves_rows_schema_and_ids(legacy_copy, tmp_path, legacy_source):
    original = inspect_database(legacy_source)
    assert original["row_count"] == 29
    assert verify_backup(legacy_copy)["snapshot"]["row_count"] == 29
    restored = tmp_path / "restored.db"
    restore_backup(legacy_copy, restored)
    assert inspect_database(restored) == original
    assert sha256(restored) == sha256(legacy_copy)


@pytest.mark.parametrize("operation", ["backup", "restore"])
def test_existing_destination_never_overwritten(legacy_copy, tmp_path, operation):
    target = tmp_path / "occupied.db"
    target.write_bytes(b"preserve me")
    function = backup_database if operation == "backup" else restore_backup
    with pytest.raises(FileExistsError):
        function(legacy_copy, target)
    assert target.read_bytes() == b"preserve me"


def test_existing_manifest_never_overwritten(legacy_copy, tmp_path):
    target = tmp_path / "new.db"
    manifest_path(target).write_text("preserve manifest")
    with pytest.raises(FileExistsError):
        backup_database(legacy_copy, target)
    assert not target.exists()


def test_corrupt_backup_cannot_be_restored(legacy_copy, tmp_path):
    with legacy_copy.open("ab") as handle:
        handle.write(b"tampered")
    with pytest.raises(ValueError, match="checksum"):
        restore_backup(legacy_copy, tmp_path / "restore.db")
    assert not (tmp_path / "restore.db").exists()


def test_missing_or_mismatched_manifest_rejected(legacy_copy):
    manifest = manifest_path(legacy_copy)
    data = json.loads(manifest.read_text())
    data["snapshot"]["row_count"] = 999
    manifest.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="logical"):
        verify_backup(legacy_copy)
    manifest.unlink()
    with pytest.raises(FileNotFoundError):
        verify_backup(legacy_copy)


def test_original_destination_and_migration_are_always_refused(tmp_path, legacy_source):
    before = sha256(legacy_source)
    with pytest.raises(ValueError, match="protected"):
        upgrade(REPOSITORY_DATABASE, tmp_path / "backup.db")
    with pytest.raises(ValueError, match="protected"):
        restore_backup(tmp_path / "missing.db", REPOSITORY_DATABASE)
    assert sha256(legacy_source) == before
    assert not REPOSITORY_DATABASE.exists()


def test_additive_upgrade_preserves_every_legacy_value_and_all_costs_unknown(legacy_copy, tmp_path):
    before = inspect_database(legacy_copy)
    with sqlite3.connect(legacy_copy) as conn:
        rows = conn.execute("SELECT * FROM trades ORDER BY id").fetchall()
    result = upgrade(legacy_copy, tmp_path / "pre-upgrade.db")
    assert result["applied"] == ["001_legacy_baseline", "002_trade_cost_accounting"]
    assert result["pending"] == []
    quoted = ",".join(f'"{c}"' for c in before["columns"])
    with sqlite3.connect(legacy_copy) as conn:
        assert conn.execute(f"SELECT {quoted} FROM trades ORDER BY id").fetchall() == rows
        assert conn.execute("SELECT COUNT(*) FROM trades").fetchone()[0] == 29
        for column in ACCOUNTING_COLUMNS:
            assert conn.execute(f'SELECT COUNT(*) FROM trades WHERE "{column}" IS NOT NULL').fetchone()[0] == 0
    backup = verify_backup(tmp_path / "pre-upgrade.db")
    assert backup["snapshot"]["rows_sha256"] == before["rows_sha256"]
    restored = tmp_path / "recovered.db"
    restore_backup(tmp_path / "pre-upgrade.db", restored)
    assert inspect_database(restored) == before


def test_second_upgrade_is_a_byte_identical_noop(legacy_copy, tmp_path):
    backup = tmp_path / "backup.db"
    upgrade(legacy_copy, backup)
    before = sha256(legacy_copy)
    upgrade(legacy_copy, backup)
    assert sha256(legacy_copy) == before


@pytest.mark.parametrize("fail_after", [1, 2, 5, 12])
def test_injected_ddl_failures_roll_back_schema_ledger_and_rows(legacy_copy, tmp_path, fail_after):
    before = inspect_database(legacy_copy)
    counter = 0
    def failure(revision, statement):
        nonlocal counter
        counter += 1
        if counter == fail_after:
            raise RuntimeError("simulated power interruption")
    with pytest.raises(RuntimeError, match="simulated"):
        upgrade(legacy_copy, tmp_path / "failed-backup.db", failure_hook=failure)
    assert inspect_database(legacy_copy) == before
    assert migration_plan(legacy_copy)["applied"] == []
    upgrade(legacy_copy, tmp_path / "retry-backup.db")
    assert migration_plan(legacy_copy)["pending"] == []


@pytest.mark.parametrize("tamper", ["checksum", "revision", "schema"])
def test_migration_drift_is_rejected_without_repair(legacy_copy, tmp_path, tamper):
    upgrade(legacy_copy, tmp_path / "backup.db")
    with sqlite3.connect(legacy_copy) as conn:
        if tamper == "schema":
            conn.execute("ALTER TABLE trades RENAME COLUMN net_pnl TO missing_net_pnl")
        else:
            conn.execute(f"UPDATE schema_migrations SET {tamper}='unexpected' WHERE revision='002_trade_cost_accounting'")
    before = sha256(legacy_copy)
    with pytest.raises(ValueError):
        upgrade(legacy_copy, tmp_path / "unwanted.db")
    assert sha256(legacy_copy) == before
    assert not (tmp_path / "unwanted.db").exists()


def test_untracked_partial_schema_and_missing_baseline_are_rejected(legacy_copy):
    with sqlite3.connect(legacy_copy) as conn:
        conn.execute("ALTER TABLE trades ADD COLUMN net_pnl FLOAT")
    with pytest.raises(ValueError, match="partial"):
        migration_plan(legacy_copy)
    with sqlite3.connect(legacy_copy) as conn:
        conn.execute("ALTER TABLE trades RENAME COLUMN qty TO missing_qty")
    with pytest.raises(ValueError, match="Unrecognized"):
        migration_plan(legacy_copy)


def test_restore_refuses_to_replace_database_with_newer_records(legacy_copy, tmp_path):
    snapshot = tmp_path / "snapshot.db"
    backup_database(legacy_copy, snapshot)
    with sqlite3.connect(legacy_copy) as conn:
        conn.execute("INSERT INTO trades (id,symbol,side,qty,entry_price) VALUES (30,'NEW','BUY',1,10)")
    with pytest.raises(FileExistsError):
        restore_backup(snapshot, legacy_copy)
    assert inspect_database(legacy_copy)["row_count"] == 30
    restore_backup(snapshot, tmp_path / "recovered.db")
    assert inspect_database(tmp_path / "recovered.db")["row_count"] == 29


def test_foreign_key_corruption_is_detected(legacy_copy):
    with sqlite3.connect(legacy_copy) as conn:
        conn.execute("CREATE TABLE child (trade_id INTEGER REFERENCES trades(id))")
        conn.execute("INSERT INTO child VALUES (999)")
    with pytest.raises(ValueError, match="integrity or foreign-key"):
        inspect_database(legacy_copy)


def test_backup_includes_uncheckpointed_wal_rows(legacy_copy, tmp_path):
    conn = sqlite3.connect(legacy_copy)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA wal_autocheckpoint=0")
        conn.execute("INSERT INTO trades (id,symbol,side,qty,entry_price) VALUES (30,'WAL','BUY',1,10)")
        conn.commit()
        assert Path(str(legacy_copy) + "-wal").exists()
        snapshot = tmp_path / "wal-snapshot.db"
        backup_database(legacy_copy, snapshot)
        assert verify_backup(snapshot)["snapshot"]["row_count"] == 30
        assert inspect_database(snapshot)["rows_sha256"] == inspect_database(legacy_copy)["rows_sha256"]
    finally:
        conn.close()


def test_source_change_after_backup_aborts_upgrade(legacy_copy, tmp_path, monkeypatch):
    from backend.migrations import runner
    original_backup = runner.backup_database
    def racing_writer(source, destination):
        result = original_backup(source, destination)
        with sqlite3.connect(source) as conn:
            conn.execute("INSERT INTO trades (id,symbol,side,qty,entry_price) VALUES (30,'RACE','BUY',1,10)")
        return result
    monkeypatch.setattr(runner, "backup_database", racing_writer)
    with pytest.raises(ValueError, match="changed after backup"):
        runner.upgrade(legacy_copy, tmp_path / "backup.db")
    assert migration_plan(legacy_copy)["applied"] == []
    assert inspect_database(legacy_copy)["row_count"] == 30


def test_missing_database_or_parent_never_creates_an_application_db(tmp_path):
    missing = tmp_path / "missing.db"
    with pytest.raises(FileNotFoundError):
        migration_plan(missing)
    assert not missing.exists()


def test_failed_backup_closes_handles_and_cleans_only_its_new_files(legacy_copy, tmp_path, monkeypatch):
    from backend.tools import db_safety
    target = tmp_path / "failed.db"
    before = sha256(legacy_copy)
    def fail(*args, **kwargs):
        raise OSError("simulated manifest disk failure")
    monkeypatch.setattr(db_safety.json, "dump", fail)
    with pytest.raises(OSError, match="simulated"):
        db_safety.backup_database(legacy_copy, target)
    assert not target.exists() and not manifest_path(target).exists()
    assert sha256(legacy_copy) == before


def test_corrupt_source_is_not_promoted_to_a_backup(tmp_path):
    corrupt = tmp_path / "corrupt.db"
    corrupt.write_bytes(b"not a SQLite database")
    target = tmp_path / "snapshot.db"
    with pytest.raises(sqlite3.DatabaseError):
        backup_database(corrupt, target)
    assert not target.exists() and not manifest_path(target).exists()
