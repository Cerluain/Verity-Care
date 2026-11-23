# Saswata — context

GitHub: SD17. Role: overall direction, backend / data pipeline, integration glue, pitch narrative.

## Background relevant to this hack

- ASU MS CS. Fall 2026 CPT at Vapi Inc (SF, remote from AZ) — comfortable with Vapi agents, webhooks, Twilio integration end-to-end.
- Backend / systems focused: APIs, data pipelines, SDKs, integrations. Can do frontend when needed, less interested.
- Comfortable with Solidity + ethers.js + anvil (built AttentionRank, keeper bots, verifiable credentials demos).
- TS + Python both fluent.

## What I own in this project

- Data ingestion: pulling CMS ASP, NADAC, OpenPayments, PBJ, Nursing Home Compare into a normalized shape.
- Reconciliation / fraud-detection logic: the actual "is this claim an outlier" computation across reference-price + ownership-graph signals.
- Integration between the detection pipeline and the dashboard.
- Pitch deck narrative + judge-trap answers.
- Stretch: Vapi voice agent for resident attestation (if time permits).

## What I do NOT own

- Dashboard UI / visual polish. Need a teammate strong on frontend for this.
- Live demo narration / pitch delivery (open — happy to narrate if nobody else wants to).

## Open questions I'm tracking

- Research subagents are running: (a) how the fraud actually works mechanically, (b) tight 6h demo plan. Decisions below will be finalized when those land.
- Final primary signal: reference-price-deviation alone vs ownership-graph-overlap alone vs both-combined.
- Whether voice resident-attestation ships tonight or ships as "v2 on the slide."
- Whether we target MFCU (B2G) or consumer family (B2C) in the pitch framing.

## My ideas / direction

- Primary novelty: resident-as-oracle. The procurement signal alone is competitive; what makes us uncatchable is that we can cross-verify with the resident via voice without the facility knowing. Even if we don't ship voice tonight, the slide shows it as the architectural keystone.
- Named-dollar framing: $12B/yr (Harvard 2021 PE study) must appear in the first 10 seconds of the pitch.
- Demo must show a specific facility, a specific line item, a specific red flag — not a generic dashboard full of fake alerts.
- Prefer static pre-baked scenarios in the demo. Live data ingestion is a liability under this time budget.

## Blockers / needs

- Teammate roster + skills — need to know who does frontend before I can assign scope.
- Confirmation on venue WiFi reaching data.medicaid.gov + openpaymentsdata.cms.gov + github.com.

## Decisions I've made (bind the team)

- Target buyer = state MFCU. Pitch framed B2G.
- Scope = procurement / phantom-spending ONLY tonight. Staffing is on the slide, not in the demo.
- Voice resident-attestation = stretch, built only if procurement module is demo-ready by H4.
- No ZK primitives tonight. Hash commitments + EIP-712 signed attestations if we want any crypto element.
- Markdown-only in `contexts/`. Code lives in `apps/` once scaffolded.

## TODO sections (for teammates to drop asks here)

(empty — add your TODO sections at the bottom using the format in `contexts/README.md`)
