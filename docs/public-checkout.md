# Running a public checkout

The repository contains source code, tests, documentation, and intentional UI
images. It ships no SQLite databases, user trade records, environment files,
credentials, database backups, or generated verification artifacts.

Use Python 3.12 and Node.js for verification. From the repository root in
PowerShell:

```powershell
python -m venv .venv
$python = (Resolve-Path .venv/Scripts/python.exe).Path
& $python -m pip install -r requirements.txt -r backend/requirements.txt -r requirements-dev.txt
```

The dependencies explicitly require Pydantic 2 and Streamlit 1.57 or newer,
matching the APIs used by the source. No API key is needed for local tests or
the offline fictional examples. Live market data still depends on the existing
public data provider and network availability.

## API with a new fictional demo database

Create a fresh directory outside the checkout. Both database paths must be new;
the tool refuses to overwrite existing files or the protected repository path.

```powershell
$demoDir = Join-Path $env:TEMP ("tradepulse-demo-" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $demoDir
$demoDb = Join-Path $demoDir 'demo.db'
$demoBackup = Join-Path $demoDir 'legacy-baseline.db'
& $python -m backend.tools.create_demo_database $demoDb --backup $demoBackup
$env:TRADEPULSE_DB_PATH = $demoDb
& $python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

The tool generates 29 invented `SIM` examples and applies the two versioned
migrations with a verified baseline backup. All are fictional, including the
fixture row whose historical `is_demo` flag is false to exercise compatibility.
Futures labels, fractional quantities, missing metadata, and an unusual stop
direction deliberately test legacy preservation. They do not represent actual
contracts or trades, and no contract multiplier is inferred from those labels.

Without an explicitly selected migrated database the API returns HTTP 503 for
database-backed routes. It never creates or migrates a database during import,
startup, or health requests. The historical repository DB path stays protected.

In a separate terminal, serve the existing frontend locally:

```powershell
& $python -m http.server 5500 --bind 127.0.0.1
```

Open `http://127.0.0.1:5500/` or `/dashboard.html`. The API client defaults to offline mode. For local API testing only, set
`apiBaseUrl: "http://127.0.0.1:8000"` in `frontend/config.js` before serving
the source checkout. Restore the empty address before publishing. Static builds
generate configuration separately; see [static deployment](static-deployment.md). Cached fallback examples are fictional and visibly
marked as demo data. Accounting entry remains an API feature; the existing
frontend form/layout is preserved. Realized totals disclose mixed/unknown costs.

The separate analytics application runs with:

```powershell
& $python -m streamlit run app.py
```

The existing login/modal is a frontend demonstration, not implemented backend
authentication. Authentication and Step 3 are outside this source change.

## Test without any private database

```powershell
$testDir = Join-Path $env:TEMP ("tradepulse-tests-" + [guid]::NewGuid().ToString('N'))
& $python -B -m pytest -p no:cacheprovider --basetemp $testDir -q
node --test frontend/tests/accounting.test.cjs
node --check app.js
node --check dashboard-ui.js
node --check frontend/js/api.js
```

The suite creates deterministic fictional databases in temporary directories.
Connections through the default repository engine are prohibited in tests.
Migration checks still compare every original fixture column and all 29 IDs,
test unknown versus zero costs, rollback failures, WAL backups, restore to new
paths, and refusal to overwrite newer records. No binary fixture or original
user database is required. Runtime backup and recovery procedures are documented
in [the database runbook](database-runbook.md).

Keep generated databases, backups, manifests, caches, environment files, and
secrets outside source history. `.gitignore` is a convenience, not a replacement
for reviewing the complete staged diff and outgoing commit history.
