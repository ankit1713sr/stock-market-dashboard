# Static frontend deployment

The Vercel project hosts HTML/CSS/JavaScript only. FastAPI and Streamlit remain
separate applications. This change adds no Python entrypoint, database migration,
authentication service, or production backend connection.

## Package and verify

From the repository root with Node.js available:

```sh
node scripts/build-static.cjs
node --test frontend/tests/accounting.test.cjs frontend/tests/deployment.test.cjs
node --check app.js
node --check dashboard-ui.js
node --check frontend/js/api.js
```

The script copies exactly 17 approved frontend files into `dist/`, including
the existing images and self-hosted Inter, JetBrains Mono, and Plus Jakarta Sans
fonts with SIL licenses. Plotly remains an external pinned CDN dependency.
It refuses missing assets, symlinks, unexpected existing output files, SQLite
headers, and common secret signatures. It never recursively copies the source
tree. Review the emitted relative-path/checksum manifest before uploading.
Pattern scanning supplements human review; it cannot certify arbitrary content.

`dist/` and `.vercel/` are generated local artifacts and ignored by Git.
`.vercelignore` excludes backend source, Python dependencies, tests, environment
files, databases, backups, and caches from CLI source uploads. The exact output
allowlist is the primary protection against accidental static publication.

## Configuration

`vercel.json` explicitly sets `framework: null` (Other),
`buildCommand: node scripts/build-static.cjs`, `installCommand: ""`,
`outputDirectory: dist`, and `cleanUrls: true`. These are deployment-specific
overrides; there is no need to change project-wide settings for a CLI preview.
Do not add a Python entrypoint to resolve the earlier framework-detection error.

The source `frontend/config.js` defaults to an empty API address. The build
generates a public configuration file using **only**
`TRADEPULSE_PUBLIC_API_BASE_URL`, if explicitly supplied. The address must be
HTTPS with no credentials, query parameters, fragments, or loopback hostname.
No other environment variables are serialized into browser code. This public
address is not an API key. Never place secrets in it.

For source-only local API development, explicitly edit the public configuration
to the local API address. HTTP loopback is accepted by the browser client only
when the frontend itself is on localhost. Public packages reject loopback URLs.

Without an API the dashboard uses local browser cache or labeled fictional
examples, with an offline/no-server-persistence banner. Monetary examples on
the homepage are explicitly fictional; no adoption or performance claims are
inferred from them. API chart responses have unverified provenance because the
existing backend may synthesize data. All charts are labeled accordingly;
the static tickers are illustrations and not a live feed.

## Preview without committing or pushing

Authenticate the official Vercel CLI and link **only** this independent checkout
to the existing `stock-market-dashboard` project in scope `ankit-ee79`:

```sh
vercel link --yes --project stock-market-dashboard --scope ankit-ee79
vercel deploy --target preview --scope ankit-ee79 --yes
```

Do not pass `--prod`, promote a deployment, change production aliases, or merge
the branch. If Vercel requires changing project-wide settings, stop for explicit
approval. Linking is local metadata; select the existing project, never create a
replacement project. Keep CLI credentials outside the checkout.

Validate `/`, `/dashboard`, `/index.html`, and `/dashboard.html` (the `.html`
forms should redirect to their clean URLs), both directions of navigation,
all 17 packaged files, correct content types, and a genuine 404 for unknown
assets and backend routes. Check desktop and mobile appearance, sidebar toggle,
tabs/charts, fictional examples, and offline notices. Use preview authentication
normally; do not disable deployment protection merely to run checks.

Before separately approved production rollout, review and commit/push these
changes, verify the intended commit in a successful preview, and explicitly
approve the production source/settings/promotion. Main and production remain
unchanged until that separate decision. For rollback, retain the prior deployment
reference and promote a separately verified frontend artifact; the currently
served old deployment is incomplete and should not be considered a tested
recovery target. Database migration/cutover remains outside this procedure.
