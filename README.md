# Verity Care

VillageHacks '26 Lite — ASU Tempe, SCOB 228, Nov 22 2026.

Transparency layer for US nursing home spending and staffing, built for state Medicaid Fraud Control Units. Direction is still converging between two pillars (procurement fraud / "phantom spend" vs staffing fraud / "phantom shift") — see `contexts/01-project-brief.md` for the live decision.

## For teammates joining this repo

1. Clone, open in your editor of choice.
2. Read `AGENTS.md` first. Any AI assistant you run from this directory (Claude Code, Cursor, Codex, Hermes) auto-ingests it.
3. Read `contexts/` in order: `README.md` → `01-project-brief.md` → `02-fraud-research-brief.md` → `03-demo-plan.md`.
4. Create your own file: `contexts/<your-first-name>.md`. Use `contexts/saswata.md` as a reference.
5. Put ideas, decisions, blockers, and asks (as TODO lists with checkboxes) into your own file. Do not edit other people's files without permission.

## Stack (tentative)

Plain HTML + Tailwind + Alpine + vis-network · FastAPI + static JSON · ed25519-signed JSON evidence packets. See `contexts/03-demo-plan.md` for the full build plan.
