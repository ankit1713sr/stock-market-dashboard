"""Explicitly create and migrate a NEW fictional demo database, never on startup."""
import argparse
import json
from pathlib import Path

from backend.demo_data import create_legacy_demo
from backend.migrations.runner import upgrade
from backend.tools.db_safety import assert_disposable, manifest_path


def create_demo_database(database, backup):
    database = assert_disposable(database)
    backup = assert_disposable(backup)
    if database == backup or database.exists() or backup.exists() or manifest_path(backup).exists():
        raise FileExistsError("Demo database and backup must be distinct new paths")
    create_legacy_demo(database)
    return upgrade(database, backup)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path)
    parser.add_argument("--backup", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(create_demo_database(args.database, args.backup), indent=2))


if __name__ == "__main__":
    main()
