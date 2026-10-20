"""Non-overwriting SQLite snapshots and restore-to-new-path recovery."""
import argparse
from contextlib import closing
import hashlib
import json
import os
import sqlite3
import time
from pathlib import Path


REPOSITORY_DATABASE = Path(__file__).resolve().parents[1] / "tradepulse.db"


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def connect_readonly(path):
    path = Path(path).resolve(strict=True)
    return sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=5)


def assert_disposable(path):
    path = Path(path).resolve()
    if path == REPOSITORY_DATABASE.resolve() or (
        path.exists() and REPOSITORY_DATABASE.exists() and path.samefile(REPOSITORY_DATABASE)
    ):
        raise ValueError("Repository database is protected; use a separate disposable path")
    return path


def inspect_connection(conn):
    integrity = [r[0] for r in conn.execute("PRAGMA integrity_check")]
    foreign_keys = conn.execute("PRAGMA foreign_key_check").fetchall()
    if integrity != ["ok"] or foreign_keys:
        raise ValueError("Database integrity or foreign-key verification failed")
    columns = [r[1] for r in conn.execute("PRAGMA table_info(trades)")]
    if not columns or "id" not in columns:
        raise ValueError("Missing trades table or primary key")
    rows = conn.execute("SELECT * FROM trades ORDER BY id").fetchall()
    encoded = json.dumps(rows, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    return {
        "integrity": integrity, "foreign_keys": foreign_keys,
        "columns": columns, "row_count": len(rows),
        "ids": [r[columns.index("id")] for r in rows],
        "rows_sha256": hashlib.sha256(encoded.encode()).hexdigest(),
        "schema": conn.execute(
            "SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name"
        ).fetchall(),
        "sqlite_version": sqlite3.sqlite_version,
    }


def inspect_database(path):
    with closing(connect_readonly(path)) as conn:
        conn.execute("BEGIN")
        return inspect_connection(conn)


def manifest_path(path):
    return Path(str(path) + ".manifest.json")


def backup_database(source, destination):
    """Call with application writers paused. Copy uses SQLite's snapshot API.

    Destination and sidecar manifest must both be new. Read-only source access
    supports SQLite WAL snapshots; never copy a live main file with shutil.
    """
    source = Path(source).resolve(strict=True)
    destination = assert_disposable(destination)
    if destination.exists() or manifest_path(destination).exists():
        raise FileExistsError("Backup destination or manifest already exists")
    if source == destination:
        raise ValueError("Source and destination must differ")
    deadline = time.monotonic() + 15
    def progress(status, remaining, total):
        if time.monotonic() > deadline:
            raise TimeoutError("Backup exceeded its bounded lock/time budget")
    # Exclusive creation avoids overwriting a pre-existing destination.
    with destination.open("xb"):
        pass
    owns_manifest = False
    try:
        with closing(connect_readonly(source)) as src, closing(sqlite3.connect(destination)) as dst:
            src.execute("BEGIN")
            baseline = inspect_connection(src)
            src.backup(dst, pages=128, progress=progress, sleep=0.01)
        actual = inspect_database(destination)
        if baseline != actual:
            raise ValueError("Backup logical contents differ from source snapshot")
        result = {"format": 1, "source": str(source), "snapshot": actual,
                  "source_main_file_sha256": sha256(source),
                  "file_sha256": sha256(destination)}
        with manifest_path(destination).open("x", encoding="utf-8") as handle:
            owns_manifest = True
            json.dump(result, handle, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        return result
    except BaseException:
        destination.unlink(missing_ok=True)
        if owns_manifest:
            manifest_path(destination).unlink(missing_ok=True)
        raise


def verify_backup(path):
    path = Path(path).resolve(strict=True)
    manifest = json.loads(manifest_path(path).read_text(encoding="utf-8"))
    if manifest.get("format") != 1 or sha256(path) != manifest["file_sha256"]:
        raise ValueError("Backup checksum mismatch")
    # JSON normalizes schema tuples to lists.
    actual = json.loads(json.dumps(inspect_database(path)))
    if actual != manifest["snapshot"]:
        raise ValueError("Backup logical verification failed")
    return manifest


def restore_backup(source, destination):
    """Restore to NEW path only. Never switch the running application's path."""
    destination = assert_disposable(destination)
    if destination.exists() or manifest_path(destination).exists():
        raise FileExistsError("Restore destination or manifest already exists")
    verified = verify_backup(source)
    restored = backup_database(source, destination)
    if json.loads(json.dumps(restored["snapshot"])) != verified["snapshot"]:
        raise ValueError("Restored contents do not match the backup")
    verify_backup(source)  # detect a backup changed between verification and copy
    return restored


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["inspect", "backup", "verify", "restore"])
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path, nargs="?")
    args = parser.parse_args()
    if args.operation in {"backup", "restore"} and args.destination is None:
        parser.error("A new destination path is required")
    operations = {"inspect": lambda: inspect_database(args.source),
                  "verify": lambda: verify_backup(args.source),
                  "backup": lambda: backup_database(args.source, args.destination),
                  "restore": lambda: restore_backup(args.source, args.destination)}
    print(json.dumps(operations[args.operation](), indent=2))


if __name__ == "__main__":
    main()
