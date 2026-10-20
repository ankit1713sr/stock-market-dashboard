# Step 2: database safety and cost accounting

The repository's `backend/tradepulse.db` is protected. Maintenance writes to
that path (including resolved symlinks/hard links) are refused. The default API
connection uses SQLite read-only mode. No schema creation or migration runs
on imports, API startup, health requests, or seeder startup.

Implementation approval covers disposable databases only. Real-database
migration/cutover requires separate human approval. Do not remove the protection
or switch the production path as part of a test run.

## Revisions and historical preservation

- `001_legacy_baseline`: validates required historical columns and the `id`
  primary key; creates `schema_migrations` with checksums and UTC timestamps.
- `002_trade_cost_accounting`: adds eleven nullable columns, with no defaults,
  updates, inferred multipliers, or financial recalculation:
  `brokerage_fee`, `transaction_fee`, `slippage_cost`, `contract_multiplier`,
  `cost_status`, `slippage_treatment`, `cost_model_json`, `gross_pnl`,
  `total_costs`, `net_pnl`, `accounting_version`.

Both revisions run within one explicit `BEGIN IMMEDIATE` transaction. Every
historical column is compared before commit, ordered by ID. Integrity and
foreign-key checks must pass. A repeated upgrade validates history/schema and
does no work. Unknown revisions, modified revision checksums, or untracked
partial accounting schemas are errors; the tool never guesses or repairs them.

The baseline recognizes the current historical structure, including its nullable
fields. It does not tighten old constraints, normalize timestamps, fix old stop
directions, or rewrite indexes. Do not edit applied revision definitions;
introduce a new revision for future changes.

## Backup and verification

Use the SQLite online backup API, never a main-file copy of an active database.
It includes committed WAL contents. Source access uses `mode=ro`. A stable read
transaction covers source validation and snapshot creation. Pause application
writers for maintenance; migration rechecks the snapshot under its write lock
and aborts if the source changed after backup. Lock/backup waiting is bounded.

Destinations and `.manifest.json` sidecars must not exist. Manifests contain:
SQLite version, schema/index SQL, ordered column names/IDs, row count, canonical
JSON row SHA-256, integrity/foreign-key results, source path, source-main-file
hash, and snapshot file hash. The source-main-file hash alone is not a logical
snapshot identifier when WAL is active. The snapshot manifest is flushed/fsynced.

The public test suite generates 29 fictional legacy trades in temporary files.
No user database or trade history is included or needed. Rehearsals verify all
fixture IDs and each original column value, not merely aggregate P&L. Snapshot file bytes
are checked against their own manifest; migrated files are expected to have a
different file hash. Preserve source/backup files and manifests with restricted
filesystem permissions; SHA-256 detects accidental changes, not malicious
replacement of both a backup and its manifest.

## Disposable rehearsal commands (PowerShell, repository root)

Use the project's isolated `.venv`. Paths below must refer to a disposable input
copy and new output paths; replace placeholders deliberately. Do not point an
apply command at the repository database.

```powershell
$python = (Resolve-Path .venv/Scripts/python.exe).Path
& $python -m backend.tools.db_safety inspect '<disposable-input.db>'
& $python -m backend.tools.db_safety backup '<disposable-input.db>' '<new-snapshot.db>'
& $python -m backend.tools.db_safety verify '<new-snapshot.db>'
& $python -m backend.tools.db_safety restore '<new-snapshot.db>' '<new-restored.db>'
& $python -m backend.migrations.runner '<new-restored.db>'
& $python -m backend.migrations.runner '<new-restored.db>' --apply-disposable --backup '<new-pre-migration.db>'
& $python -m backend.migrations.runner '<new-restored.db>'
```

The runner defaults to read-only planning unless `--apply-disposable` is given.
Applied upgrades always create and verify their own new pre-migration backup.
A second apply is a no-op and does not overwrite/recreate its backup.

To serve only an explicitly selected, already migrated disposable database:

```powershell
$env:TRADEPULSE_DB_PATH = '<absolute-path-to-migrated-disposable.db>'
& $python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

The default repository DB remains read-only even if selected explicitly.
An unmigrated trades schema returns HTTP 503 with a migration explanation rather
than issuing DDL or failing an ORM query for missing accounting columns.
Missing database files are not automatically created. To initialize a NEW,
separate fictional demo database explicitly, run:

```powershell
& $python -m backend.tools.create_demo_database '<new-absolute-demo.db>' --backup '<new-absolute-demo-baseline.db>'
```

This creates deterministic legacy examples and applies the two explicit revisions
with a verified pre-migration backup. Existing database/backup destinations and
the protected repository path are refused. Set `TRADEPULSE_DB_PATH` to the new
demo path before starting the API. Neither startup nor tests require a private
database. ORM `create_all` is used only for disposable test fixtures.

## Accounting contract

Amounts are round-trip totals in the same currency as prices/notional. There is
no FX conversion. Execution prices are actual fills unless intentionally modeling
additional slippage. The API does not infer futures/options specifications.

Legacy requests without accounting fields retain legacy zero-deduction behavior.
For the existing records all new columns remain NULL; their stored P&L, return,
risk, and R-multiple are unchanged. Their basis is `legacy_unknown`, not evidence
of zero fees. A financial edit is an explicit user operation; metadata-only edits
never recalculate financial results or fill missing legacy fields.

Opting into accounting requires an explicit positive `contract_multiplier`:

- `cost_status=unknown`: any missing costs remain NULL; `total_costs` and
  `net_pnl` remain NULL. Compatibility `pnl`/return/R use gross P&L and are labeled
  `gross_unknown_costs`. Known partial charges may be retained without claiming
  a fully known net result.
- `cost_status=reported`: provide all three nonnegative values `brokerage_fee`,
  `transaction_fee`, `slippage_cost`, including explicit zeros, and a
  `slippage_treatment`. `included` requires additional slippage cost zero because
  it is already in execution prices; `additional` subtracts the specified amount.
- `cost_status=estimated`: supply `cost_model` and treatment `additional`, with no
  explicit fee/slippage totals. Its validated configuration is stored as JSON.
  The model supports `fee_per_order`, `fee_bps`, `slippage_bps`, `min_fee`,
  `max_fee`; commission floors/caps apply before slippage, on each entry/exit.

For known costs, gross P&L = direction × (exit − entry) × qty × multiplier;
net P&L = gross − total costs. Compatibility `pnl` equals net. Return percentage
uses entry notional; R uses net P&L divided by absolute stop distance × qty ×
multiplier, retaining the existing legacy stop-distance convention. Open trades
have no realized P&L/returns/R, even when their fees are provided. Closing them
uses the supplied whole-trade totals. Reopening clears realized results.

Results use the validated quant engine's existing float/rounding conventions
(money to two decimals, returns/R to four); this is not an exact-decimal general
ledger. Nonfinite inputs/results are rejected. Brokerage/transaction categories
are explicit inputs; estimated commissions remain identified by model snapshot.

Example reported-cost request:

```json
{
  "symbol": "TEST", "side": "BUY", "qty": 10,
  "entry_price": 100, "exit_price": 110, "stop_loss": 95,
  "contract_multiplier": 1, "cost_status": "reported",
  "brokerage_fee": 2, "transaction_fee": 3, "slippage_cost": 5,
  "slippage_treatment": "additional"
}
```

This returns gross 100, costs 10, net/compatibility P&L 90, return 9%, risk 50,
and R=1.8. Derived fields are server-controlled. PUT retains omitted fields;
explicit NULL clears optional inputs, and zero remains zero. Changing from an
estimate to reported costs requires explicitly clearing `cost_model` with NULL.
Invalid updates roll back rather than partially saving input changes.

## Reporting and frontend compatibility

The existing routes, aliases, and dashboard-summary top-level keys remain.
GET `/api/v1/analytics/cost-coverage` supplies completed-trade basis counts,
`fully_costed`, and a label. Each trade exposes `pnl_basis` and nullable accounting
fields. Dashboard `net_pnl` retains its compatibility name: in a mixed ledger
it sums net results where known and historical/gross results where costs are
unknown. It must not be presented as fully cost-adjusted net profit.

Dashboard, equity curve, calendar realized amounts, strategy/emotion/mistake
analytics, returns, and R use the same basis. Open trades remain visible in the
calendar and journal; they do not contribute realized P&L. Calendar `trade_count`
continues to count visible entries. Journal Sharpe/Sortino remain nonannualized
per-trade ratios with the existing 10,000 initial-equity convention.

The dashboard displays mixed/unknown reporting explicitly. Cached trades retain
their accounting fields and net P&L, including known zero. Cost-aware trades
cannot be edited offline or silently replaced with a browser gross calculation
after a failed API save. Cost entry is currently an API feature; the existing
trade form/layout is preserved. Browser/local-cache mode is not a synchronized
accounting database or a replacement for server backup.

## Recovery and rollout gate

1. Keep writers stopped and preserve the current database, backups, manifests,
   source revision, and logs. Never delete newer records to make an old backup fit.
2. Verify the selected backup; restore to a NEW path and verify it independently.
3. If there have been post-migration writes, retain the newer database. An older
   backup cannot represent those records; reconcile them before any cutover.
4. Application rollback may retain additive columns, but run read-only until
   compatibility is checked: older code can overwrite net results on edits.
5. Obtain separate approval before changing the real application database path.
   In-place migration/restoration of the repository DB remains intentionally blocked.

Run all existing 94 Python tests plus the Step 2 suite on isolated sources and
disposable databases, then `node --test frontend/tests/accounting.test.cjs` and
`node --check` for all production JavaScript files. Tests cover WAL backup,
restore verification, no-overwrite recovery, migration retries/checksum drift,
source changes after backup, injected DDL failures, preservation of every legacy
column, cost math, unknown versus zero, API consistency and cache safety.

Backups should also be retained off-device under the user's storage policy;
this local tooling does not implement remote backup retention or encryption.
Authentication and Step 3 are outside this change.
