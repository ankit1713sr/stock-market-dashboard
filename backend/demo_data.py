"""Deterministic fictional examples, never derived from a user's database.

The legacy fixture deliberately retains missing metadata, fractional quantities,
four unscaled Futures labels, and an unusual stop direction for migration tests.
"""
import sqlite3
from contextlib import closing
from datetime import date, timedelta
from pathlib import Path

from backend.migrations.revisions import LEGACY_COLUMNS
from backend.tools.db_safety import assert_disposable


LEGACY_SCHEMA = """CREATE TABLE trades (
    id INTEGER PRIMARY KEY, symbol VARCHAR, side VARCHAR, qty FLOAT,
    entry_price FLOAT, exit_price FLOAT, pnl FLOAT, strategy VARCHAR,
    created_at DATETIME, trade_date VARCHAR(10), asset VARCHAR(50),
    stop_loss FLOAT, target_price FLOAT, return_pct FLOAT, risk_amount FLOAT,
    r_multiple FLOAT, emotion VARCHAR(50), mistake VARCHAR(80), rating INTEGER,
    notes TEXT, chart_url TEXT, updated_at DATETIME, is_demo BOOLEAN NOT NULL DEFAULT 0
)"""


def fictional_trades(count=29):
    """Return entirely invented, stable examples with IDs 1..count."""
    result = []
    for number in range(1, count + 1):
        entry = 37.0 + number * 1.125
        direction = 1 if number % 2 else -1
        side = "BUY" if direction == 1 else "SELL"
        qty = 1 + (number % 7) * 0.25
        exit_price = entry + (0.4 + number * 0.025) * (-1 if number % 3 else 1)
        stop = entry - direction * 2
        if number == 29:
            stop = entry + direction  # intentional historical-validation edge case
        pnl = round(direction * (exit_price - entry) * qty, 2)
        risk = abs(entry - stop) * qty
        day = (date(2019, 1, 1) + timedelta(days=number - 1)).isoformat()
        result.append(dict(
            id=number, symbol=f"SIM{number:03d}", side=side, qty=qty,
            entry_price=entry, exit_price=exit_price, pnl=pnl,
            strategy="Example Trend" if number % 2 else "Example Reversal",
            created_at=day + " 12:00:00", trade_date=day,
            asset=None if number == 1 else ("Futures" if number >= 26 else "Stock"),
            stop_loss=stop, target_price=entry + direction * 4,
            return_pct=round(direction * (exit_price - entry) / entry * 100, 4),
            risk_amount=round(risk, 2), r_multiple=round(pnl / risk, 4),
            emotion="Disciplined", mistake="None", rating=3,
            notes=f"FICTIONAL EXAMPLE {number:03d}; not a real trade.", chart_url="",
            updated_at=day + " 12:00:00", is_demo=number != 1,
        ))
    return result


def create_legacy_demo(path):
    """Create only a new, explicitly selected disposable legacy database."""
    path = assert_disposable(Path(path))
    with path.open("xb"):
        pass
    try:
        with closing(sqlite3.connect(path)) as conn:
            conn.execute(LEGACY_SCHEMA)
            conn.execute("CREATE INDEX ix_trades_id ON trades (id)")
            conn.execute("CREATE INDEX ix_trades_symbol ON trades (symbol)")
            names = ",".join(f'"{name}"' for name in LEGACY_COLUMNS)
            placeholders = ",".join("?" for _ in LEGACY_COLUMNS)
            conn.executemany(f"INSERT INTO trades ({names}) VALUES ({placeholders})", [
                tuple(row[name] for name in LEGACY_COLUMNS) for row in fictional_trades()
            ])
            conn.commit()
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    return path
