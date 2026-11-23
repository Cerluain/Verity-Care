# AGENTS.md — Verity Care (VillageHacks '26 Lite)

Any AI assistant run from this directory (Claude Code / Cursor / Codex / Hermes) should load this file first, then read the `contexts/` folder in full before acting.

## One-line pitch

Verity Care — a continuous, verifiable transparency layer for US nursing home spending and staffing, targeted at state Medicaid Fraud Control Units.

Scope and primary signal are still converging. See `contexts/01-project-brief.md` for the live direction.

## Hard constraints

- Event: VillageHacks '26 Lite, ASU Tempe, SCOB 228. Nov 22 2026, 11:00 AM MST – 11:45 PM MST. ~12h 45m total.
- Format: in-person, single judging axis ("challenge solution" — innovation + technical quality + real-world impact).
- Judges: one tech, one government-adjacent domain. No sponsor prize matrix on this edition.
- Time left at scaffold time: ~6–7 hours of real build time before demo rehearsal.
- Team size: ~2–3, roles TBD. See owner map below once filled.

## Non-negotiables

- Grounding: every data point in the demo must trace to a real public source (CMS ASP file, NADAC, OpenPayments, DOJ settlement, OIG report) or be clearly labelled "synthetic / illustrative" in the UI. No invented stats passed off as real.
- No facility cooperation assumed: the pitch's moat is that this works without needing the nursing home to expose its EHR. Any feature that requires facility APIs is out of scope for the demo.
- Privacy: no real resident names / PHI, even in mock data. Use obviously-synthetic identifiers.
- Scope discipline: 60–90 second demo arc drives everything. If a feature doesn't appear in the arc, it doesn't get built in the next 6 hours.

## Rules for AI agents reading this

1. Read `contexts/01-project-brief.md` + every file under `contexts/` before proposing changes.
2. Before writing code, confirm the demo arc section of `contexts/01-project-brief.md` is settled. If not, surface that and wait.
3. Do not commit secrets. `.env` is gitignored. Every new env var needs a matching `.env.example` entry in the same commit.
4. Prefer static JSON + pre-baked scenarios over live data ingestion for anything in the demo arc. Reliability > novelty under this time budget.
5. When writing asks into a teammate's `contexts/<name>.md`, use the TODO-list format: `[ ]` checkbox, priority marker, time estimate, one-line goal, code sketch where applicable. No prose asks.
6. When a design decision is reversed mid-hack, update BOTH `AGENTS.md` and `contexts/01-project-brief.md` atomically. Do not leave stale text that contradicts the new direction.

## Secrets rule

Every third-party API key / token / credential MUST have a matching `.env.example` in the same commit it's introduced. Service-local → `apps/<app>/.env.example`. Cross-app → repo-root `.env.example`.

## Owner map

(fill in once teammates self-assign)

- Saswata (SD17) — overall direction, backend/data, integration
- TBD — frontend / dashboard
- TBD — pitch deck / demo rehearsal

## Current status

**LOCKED. Build phase starting.**

Research complete, direction frozen. Read in order: `contexts/01-project-brief.md` (pitch + scope + stack), `contexts/02-fraud-research-brief.md` (what the fraud actually is, why price-scraping is a strawman), `contexts/03-demo-plan.md` (hour-by-hour schedule + full pitch script).

Headline: we build a 3-signal fraud detector fusing (1) reference-price delta, (2) ownership-graph overlap, (3) PBJ volume-vs-census sanity. Single HTML dashboard + FastAPI + static JSON. No chain. No ZK. No Vapi in v1.

Target buyer: state Medicaid Fraud Control Units.
