"""Versioned migration runner. Repository database is unconditionally protected."""
import argparse
from contextlib import closing
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from backend.migrations.revisions import ACCOUNTING_COLUMNS, LEGACY_COLUMNS, REVISIONS
from backend.tools.db_safety import (
    assert_disposable, backup_database, inspect_connection, inspect_database, verify_backup,
)


def revision_checksum(revision, statements):
    return hashlib.sha256(json.dumps([revision, LEGACY_COLUMNS, statements]).encode()).hexdigest()


def plan_connection(conn):
    snapshot = inspect_connection(conn)
    names = set(snapshot["columns"])
    if not set(LEGACY_COLUMNS) <= names:
        raise ValueError("Unrecognized legacy schema; no automatic repair is permitted")
    info = {r[1]: r for r in conn.execute("PRAGMA table_info(trades)")}
    if info["id"][5] != 1:
        raise ValueError("trades.id must be the primary key")
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    applied = []
    if "schema_migrations" in tables:
        applied = conn.execute("SELECT revision,checksum FROM schema_migrations ORDER BY revision").fetchall()
    expected = [(r, revision_checksum(r, statements)) for r, statements in REVISIONS]
    if applied != expected[:len(applied)]:
        raise ValueError("Unknown, out-of-order, or checksum-mismatched migration history")
    added = set(ACCOUNTING_COLUMNS) & names
    if len(applied) < 2 and added:
        raise ValueError("Untracked/partial accounting schema; refusing to guess")
    if len(applied) == 2:
        for name, ddl in ACCOUNTING_COLUMNS.items():
            row = info.get(name)
            if not row or row[2].upper() != ddl or row[3] != 0 or row[4] is not None:
                raise ValueError(f"Accounting schema drift: {name}")
    return {"applied": [r for r, _ in applied],
            "pending": [r for r, _ in expected[len(applied):]], "snapshot": snapshot}


def migration_plan(path):
    from backend.tools.db_safety import connect_readonly
    with closing(connect_readonly(path)) as conn:
        conn.execute("BEGIN")
        return plan_connection(conn)


def upgrade(path, backup_path, *, failure_hook=None):
    """Upgrade separate path only, with verified backup and all-or-nothing DDL.

    failure_hook is an injectable test seam called after each statement.
    The caller must pause all application writers for the rehearsal/deployment.
    """
    path = assert_disposable(path).resolve(strict=True)
    assert_disposable(backup_path)
    plan = migration_plan(path)
    if not plan["pending"]:
        return plan  # repeat execution must not create another backup or write
    backup_database(path, backup_path)
    verified = verify_backup(backup_path)
    with closing(sqlite3.connect(path, timeout=5, isolation_level=None)) as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            locked = plan_connection(conn)
            if json.loads(json.dumps(locked["snapshot"])) != verified["snapshot"]:
                raise ValueError("Database changed after backup; refusing migration")
            columns = locked["snapshot"]["columns"]
            quoted = ",".join('"' + c.replace('"', '""') + '"' for c in columns)
            before = conn.execute(f"SELECT {quoted} FROM trades ORDER BY id").fetchall()
            for revision, statements in REVISIONS:
                if revision not in locked["pending"]:
                    continue
                for statement in statements:
                    conn.execute(statement)
                    if failure_hook:
                        failure_hook(revision, statement)
                conn.execute("INSERT INTO schema_migrations VALUES (?,?,?)",
                             (revision, revision_checksum(revision, statements),
                              datetime.now(timezone.utc).isoformat()))
            if before != conn.execute(f"SELECT {quoted} FROM trades ORDER BY id").fetchall():
                raise ValueError("Historical trade values changed; rolling back")
            inspect_connection(conn)
            plan_connection(conn)
            conn.execute("COMMIT")
        except BaseException:
            conn.execute("ROLLBACK")
            raise
    return migration_plan(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path)
    parser.add_argument("--backup", type=Path)
    parser.add_argument("--apply-disposable", action="store_true")
    args = parser.parse_args()
    if args.apply_disposable and not args.backup:
        parser.error("--backup NEW_PATH is required")
    result = (upgrade(args.database, args.backup) if args.apply_disposable
              else migration_plan(args.database))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
