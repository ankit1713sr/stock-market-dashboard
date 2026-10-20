"""Immutable revision definitions. No defaults/backfill on historical trades."""

LEGACY_COLUMNS = (
    "id", "symbol", "side", "qty", "entry_price", "exit_price", "pnl", "strategy",
    "created_at", "trade_date", "asset", "stop_loss", "target_price", "return_pct",
    "risk_amount", "r_multiple", "emotion", "mistake", "rating", "notes", "chart_url",
    "updated_at", "is_demo",
)

ACCOUNTING_COLUMNS = {
    "brokerage_fee": "FLOAT", "transaction_fee": "FLOAT", "slippage_cost": "FLOAT",
    "contract_multiplier": "FLOAT", "cost_status": "VARCHAR(20)",
    "slippage_treatment": "VARCHAR(20)", "cost_model_json": "TEXT",
    "gross_pnl": "FLOAT", "total_costs": "FLOAT", "net_pnl": "FLOAT",
    "accounting_version": "INTEGER",
}

REVISIONS = (
    ("001_legacy_baseline", [
        "CREATE TABLE schema_migrations (revision TEXT PRIMARY KEY, checksum TEXT NOT NULL, "
        "applied_at TEXT NOT NULL)"
    ]),
    ("002_trade_cost_accounting", [
        f'ALTER TABLE trades ADD COLUMN "{name}" {ddl}'
        for name, ddl in ACCOUNTING_COLUMNS.items()
    ]),
)
