# NHL Moment-to-Market Intelligence Lab

Public-evidence research on how objectively defined NHL moments coincide with independently observable attention signals. It is not a commercial forecast, ticketing model, CRM system, sponsor-valuation tool, or sentiment product.

## Decision

For every club: which recurring hockey moments show a reproducible public-attention response, and what should content, marketing, partnerships, communications, and strategy teams test in the following 24 hours, 72 hours, and seven days?

## Local build and release

Create the declared analytical environment with `python3 -m venv .venv` and `.venv/bin/python -m pip install -e .`. Then run `npm run build:analytics`, `npm run build`, `npm test`, and `npm run validate` from this directory after source acquisition is complete. The npm scripts deliberately use `.venv/bin/python` so the model cannot silently fall back when NumPy, pandas, or statsmodels are absent from the system interpreter. Pipelines retain raw source records with URL, retrieval time, checksum, and schema/version information before curated output is generated. The validator blocks a release when any full-league source, model, memo, website, or commercial-claim gate fails.

## Current scope

The shared system covers 2015–16 through 2025–26 for all eligible club-seasons and keeps Arizona’s historical identity separate from Utah’s later validity periods. Vegas, Seattle, and Utah enter only when they begin NHL play. Coverage is explicit; unavailable evidence never becomes zero or a positive finding. Club pages are generated from one shared data model at `/clubs/[club-slug]`.
