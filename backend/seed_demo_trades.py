"""Development-only demo data seeder for TradePulse AI.

Usage:
  python backend/seed_demo_trades.py          # add demo rows only if absent
  python backend/seed_demo_trades.py --clear  # remove demo rows only
  python backend/seed_demo_trades.py --reset  # clear and reinsert demo rows

Rows are marked with is_demo=True and notes prefixed with [DEV_DEMO].
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys

# Support both module and direct-script invocation without importing root app.py.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.database import SessionLocal, engine, _DB_PATH
from tools.db_safety import assert_disposable
from app.models import Trade
from app.services import calculate_trade_metrics


@dataclass(frozen=True)
class DemoTrade:
    trade_date: str
    symbol: str
    side: str
    qty: float
    entry_price: float
    exit_price: float
    stop_loss: float
    target_price: float
    strategy: str
    emotion: str
    mistake: str
    rating: int
    asset: str = "Stock"


# Fictional examples only: no user database rows are embedded in source.
from backend.demo_data import fictional_trades
DEMO_TRADES = [
    DemoTrade(**{name: row[name] for name in DemoTrade.__dataclass_fields__})
    for row in fictional_trades(28)
]


def build_trade(row: DemoTrade) -> Trade:
    metrics = calculate_trade_metrics(
        row.side,
        row.entry_price,
        row.exit_price,
        row.qty,
        row.stop_loss,
    )
    return Trade(
        trade_date=row.trade_date,
        symbol=row.symbol,
        side=row.side,
        asset=row.asset or "Stock",
        qty=row.qty,
        entry_price=row.entry_price,
        exit_price=row.exit_price,
        stop_loss=row.stop_loss,
        target_price=row.target_price,
        strategy=row.strategy,
        emotion=row.emotion,
        mistake=row.mistake,
        rating=row.rating,
        notes="[DEV_DEMO] FICTIONAL EXAMPLE; not a real trade.",
        is_demo=True,
        **metrics,
    )


def clear_demo_trades(db) -> int:
    count = db.query(Trade).filter(Trade.is_demo.is_(True)).count()
    db.query(Trade).filter(Trade.is_demo.is_(True)).delete(synchronize_session=False)
    db.commit()
    return count


def seed_demo_trades(reset: bool = False) -> int:
    assert_disposable(_DB_PATH)
    db = SessionLocal()
    try:
        if reset:
            clear_demo_trades(db)

        existing = db.query(Trade).filter(Trade.is_demo.is_(True)).count()
        if existing:
            return 0

        db.add_all(build_trade(row) for row in DEMO_TRADES)
        db.commit()
        return len(DEMO_TRADES)
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed development-only TradePulse demo trades.")
    parser.add_argument("--clear", action="store_true", help="Remove demo trades only.")
    parser.add_argument("--reset", action="store_true", help="Remove and recreate demo trades.")
    args = parser.parse_args()

    assert_disposable(_DB_PATH)
    db = SessionLocal()
    try:
        if args.clear:
            removed = clear_demo_trades(db)
            print(f"Removed {removed} development demo trades.")
            return
    finally:
        db.close()

    inserted = seed_demo_trades(reset=args.reset)
    print(f"Inserted {inserted} development demo trades.")


if __name__ == "__main__":
    main()
