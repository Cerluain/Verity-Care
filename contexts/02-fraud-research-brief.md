# Nursing Home Procurement/Supply/Billing Fraud — Reality Check for VillageHacks

**Audience:** hackathon team deciding what to build in the next 6h.
**TL;DR:** The "nursing home bills $50 for $5 insulin" story is a strawman. SNF Medicare
Part A is a **bundled per-diem** — individual drugs/supplies are never line-itemed on the
claim. The real money is stolen two levels up: (1) **therapy/acuity upcoding** inside the
per-diem, and (2) **related-party cost-report inflation** that ratchets up the state
Medicaid per-diem rate itself. A reference-price-comparison tool (billed vs. NADAC/ASP)
catches **neither**. Build an ownership-graph + cost-report related-party-markup detector,
or a resident/family attestation-of-services tool. Not a price scraper.

---

## 1. Top documented cases, last ~10 years, and the EXACT mechanic

(Dollar figures and years from DOJ settlement announcements and OIG reports; verify
current URLs via justice.gov search — many `/opa/pr/...` paths were restructured in May
2025, so Google the settlement name.)

| # | Chain / Entity | Year | $ | Exact mechanic |
|---|---|---|---|---|
| 1 | **Life Care Centers of America** | 2016 | $145M FCA settlement | Corporate-level pressure to push every Medicare Part A resident into **RUG-IV "Ultra High" therapy category** (720+ min/week) regardless of clinical need. Upcoding at the **service-code / assessment level (MDS 3.0)** — not supplies. |
| 2 | **RehabCare / Kindred Healthcare** | 2016 | $125M | Same: inflating therapy minutes on MDS to hit Ultra-High RUG; "ramping" therapy at end of look-back window to game the assessment. |
| 3 | **Ensign Group** | 2013 | $48M | Upcoding therapy minutes + medically unnecessary therapy. |
| 4 | **SavaSeniorCare** | 2021 | $11.2M (plus earlier) | Same — Ultra-High RUG upcoding, corporate-mandated targets. |
| 5 | **Signature HealthCARE** | 2018 | $30M | Upcoding therapy minutes; falsified pre-admission screenings. |
| 6 | **Consulate Health Care** | 2023 | $4.5M (settled down from a ~$256M jury verdict reduced for inability to pay — the *Ruckh* qui tam) | Upcoding + record falsification; notable because the operator was essentially judgment-proof, structured as thin single-purpose LLCs. |
| 7 | **Vanguard Healthcare** | 2017 | $18M | **"Worthless services"** theory — billed for care (incl. wound/med management) so deficient it was legally worthless. Closest thing to classic supply fraud but framed as service failure, not invoice inflation. |
| 8 | **HCR ManorCare** | 2020 | $8.3M | Therapy upcoding (Carlyle-era conduct; Carlyle exited via distress). |
| 9 | **Omnicare (CVS)** | 2015 ($8M), 2020 ($15.3M), earlier $124M (2014) | ~$150M+ cumulative | **Kickbacks**: paid SNFs (via "consulting fees," discounted IV meds, data services) in exchange for exclusive long-term-care pharmacy contracts. Not overbilling the resident — paying the home to steer scripts. |
| 10 | **PharMerica** | 2015 $31.5M, 2023 $5.5M | | Controlled-substance dispensing without valid orders; billing Medicare Part D for non-compliant dispenses. |
| 11 | **Philip Esformes (Miami SNF/ALF network)** | 2019 conviction, $1.3B scheme | — | **Kickbacks + cycling**: paid recruiters to move same patients through his SNFs/ALFs/hospitals for medically unnecessary stays. Most famous nursing-home-adjacent fraud ever; still not supply-invoice fraud. |
| 12 | **Skyline Healthcare / Joseph Schwartz** | 2023 indictment | $38M payroll-tax fraud; ~100 homes collapsed 2018–2019 | **Ownership-opacity + looting**: acquired distressed homes nationwide via opaque LLC web, drained operating cash, didn't pay staff/vendors/taxes. The best public example of the sister-LLC structure in collapse — bankruptcy filings exposed the graph. |

**Pattern:** ~80% of large SNF FCA settlements since 2015 are **therapy upcoding** under the
old RUG-IV system (replaced by PDPM Oct 2019; expect PDPM-era cases to shift to **ICD-10
diagnosis upcoding** and **Section GG ADL inflation**). The remainder are
pharmacy-kickback and worthless-services. **Zero** of the big cases are "faked a $50
invoice for $5 insulin."

---

## 2. Where does the $45 markup actually land? (The critical mechanics question)

This is where the hackathon framing breaks. Walk through it carefully:

### Medicare Part A SNF (post-hospital stays, up to 100 days)
- Paid as a **per-diem** under **PDPM** (Oct 2019+). Drugs, IV supplies, routine wound
  care, insulin pens, incontinence supplies — all **bundled into the daily rate**.
- There is **no line item on the claim** for "insulin, $50." The MDS assessment drives
  five case-mix components (PT, OT, SLP, Nursing, NTA) → per-diem.
- → **(a) fake-invoice fraud is structurally impossible on the Part A claim itself.**
- The real fraud lever is **(e) service-code / assessment upcoding**: push the resident
  into a higher PDPM Nursing or NTA tier by over-reporting IV meds, isolation, diabetes
  complications, special-care conditions on the MDS. A single extra NTA point can move
  the per-diem by $20–$80/day for ~30 days.

### Medicare Part B (outpatient-style services inside SNF, after Part A exhaust)
- HCPCS/J-codes **are** line-itemed (therapy minutes, some drugs). Reference-price
  checking (ASP, NADAC) is plausible **here only**, and it's a sliver of SNF revenue.

### Medicare Part D (long-term-care pharmacy — Omnicare/PharMerica)
- The **pharmacy** bills Part D, not the home. Fraud is kickbacks *to* the home for
  exclusivity, not price markup *by* the home. NADAC comparison does flag some of this
  but CMS already runs it.

### Medicaid (long-stay custodial — 60%+ of SNF resident-days, where the real money is)
- Each state uses a **prospective per-diem or price-based rate** calibrated from the
  facility's **CMS Form 2540-10 Medicare/Medicaid Cost Report** (filed annually).
- Supplies, drugs, dietary, laundry, management, rent — all flow through the cost report
  as **operating costs**. Higher reported cost → higher state per-diem next rate cycle.
- **Related-party transactions** are supposed to be reported on **Worksheet A-8-1** at
  **cost to the related organization**, not at the marked-up transfer price. In practice
  they are routinely not reported, or reported at the transfer price with no challenge.
  HHS OIG has flagged this repeatedly (see OIG report OEI-02-20-00490, and the Nov 2024
  OIG report on SNF related-party disclosures).
- So the **$5 insulin / $50 billed** structure works like this:
  1. ParentCo LLC owns NursingHome LLC and PharmacyCo LLC.
  2. PharmacyCo buys insulin wholesale for $5.
  3. PharmacyCo "sells" to NursingHome for $50 — real invoice, real wire, real tax
     return. This is **not fake**; it is a legitimate intercompany transaction.
  4. NursingHome reports $50/dose as operating cost on Form 2540.
  5. State Medicaid rate-setting folds that into the per-diem → every Medicaid
     resident-day pays slightly more forever. **The $45 lands as PharmacyCo profit**, which
     distributes up to ParentCo, often offshore or to a PE fund.

### Dominant mechanic answer
- Volume-weighted: **(b) related-party markup via cost-report inflation** is by far the
  largest dollar vector, but it is **rarely prosecuted** because it requires proving the
  transfer price was not arm's-length. It mostly shows up in academic/OIG studies as
  "tunneling."
- Prosecuted-case-weighted: **(e) service-code upcoding** dominates. That's where FCA
  qui tams land because whistleblowers (therapists, DONs) see it directly.
- **(a), (c), (d)** are rare at scale. Phantom billing happens in home-health and DME, not
  SNF Part A.

---

## 3. How procurement fraud is currently detected

- **MFCUs (state Medicaid Fraud Control Units):** ~80% of their SNF caseload is **qui tam
  whistleblower complaints** (therapists, nurses, billing clerks) + resident/family
  abuse complaints that during investigation uncover billing fraud. Data tools are
  mostly SURS (Surveillance & Utilization Review Subsystem) — 1990s-era claims
  anomaly reports. See HHS OIG annual MFCU report.
- **CMS / UPIC contractors (Unified Program Integrity Contractors):** run claims-pattern
  analysis — RUG/PDPM category mix outliers, therapy intensity vs. peer SNFs, re-hospital
  rates vs. billed acuity. Detects upcoding, not procurement.
- **OIG audits:** periodic cost-report audits sampling related-party disclosures. Very
  low coverage — a given facility sees a federal cost-report audit roughly once a decade.
- **Typical lag:** fraud → settlement = **4–8 years**. Ruckh/Consulate: conduct 2011–2013,
  verdict 2017, settlement 2023. Life Care: conduct 2006–2012, settlement 2016.

---

## 4. Named villains and ownership opacity

- **Chains with documented fraud or worthless-services findings:** Life Care Centers,
  Kindred/RehabCare, Ensign, SavaSeniorCare, Signature HealthCARE, Consulate, Vanguard,
  HCR ManorCare, Golden Living, Genesis HealthCare (ongoing state actions; large staffing
  shortfall cases), Skyline/Schwartz, Centers Health Care (NY AG action 2023 — alleged
  $83M siphoning via related parties at four NYC-area homes; exemplary public filing).
- **PE / holding villains:** Formation Capital (ManorCare, Genesis exposure), Carlyle
  Group (ManorCare acquisition → bankruptcy), Fillmore Capital (Beverly), Portopiccolo
  Group (Accordius — multiple state actions), Welltower + ProMedica (ManorCare 2022
  collapse). See Gupta/Howell/Yannelis NBER w28474 "Owner Incentives and Performance in
  Healthcare: Private Equity Investment in Nursing Homes" — documents ~10% mortality
  increase + explicit tunneling-to-related-party-management/real-estate channel.
- **Ownership opacity:** NYT investigation "Maggots, Rape and Yet Five Stars" (Mar 2021)
  and the **"Powerful Nursing Home Group…" / "How Nursing Homes' Worst Offenses Are
  Hidden"** (Sep 2022) series. Vincent Mor + David Grabowski "Where Does the Money Go?"
  Health Affairs — ~$11B/yr flows to related parties, typically 25% markup over cost.

---

## 5. Public data sources a third party can actually use

| Source | What it gives you | Fraud signal |
|---|---|---|
| **CMS SNF Cost Reports (HCRIS, Form 2540-10)** — downloadable as a flat file from cms.gov/data | Line-item costs, revenues, related-party disclosures (Worksheet A-8-1), ownership (Worksheet S-2) | **Related-party % of operating cost**; markup vs. peer medians; year-over-year cost jumps uncorrelated with acuity |
| **CMS Care Compare / Provider Data Catalog** | Star ratings, deficiencies, staffing (PBJ), ownership (new 2023 disclosure requirement under 42 CFR 424.516 — includes PE and REIT ownership flags) | Ownership graphs; identify common owners/managers across homes |
| **PBJ (Payroll-Based Journal)** | Daily nurse/aide hours per resident | Discrepancy between reported acuity (justifying high PDPM) and actual nursing hours |
| **MDS 3.0 aggregate / Nursing Home Compare quality measures** | Case-mix, long-stay quality | Upcoding signature: PDPM NTA tier mix drifting above state median |
| **OpenPayments (CMS)** | Physician payments from drug/device mfrs | Pharma-SNF kickback adjacent (less useful for SNF directly) |
| **State AG / DOH filings, bankruptcy dockets (PACER)** | Related-LLC schedules, intercompany agreements surface here | **Gold mine** — Skyline, Consulate, and multiple Portopiccolo facility bankruptcies dumped org charts |
| **Medicare Enrollment / PECOS Ownership File** (expanded Jan 2024 under the Nursing Home Ownership rule) | Direct + indirect owners ≥5%, officers, managing employees | Build the ownership graph |
| **State Medicaid rate files** | Per-diem rates by facility | Cross-reference to cost-report inputs |
| **SNF PPS Pricer** | How Medicare computes per-diem | Needed only to interpret PDPM claims |
| **NADAC / Medicaid ASP** | Benchmark drug prices | Useful **only** for Part B / Part D cross-check, barely applicable to SNF Part A |

---

## 6. Does a reference-price tool catch related-party markup? **No.**

- The facility's claim doesn't list "insulin $50." Medicare Part A has no line for it.
- The cost report lists it as "pharmacy expense — related party $50" (if they bother
  disclosing). The facility's defense is exactly what the brief anticipated: "yes, our
  real invoice from PharmacyCo is $50. Here it is. It's a real company. It has
  employees." The transfer price is only challengeable with an arm's-length benchmark
  **and** proof of common ownership **and** proof the markup is unreasonable.
- A price scraper vs. Amazon/NADAC is a **strawman solution to a strawman problem.** CMS
  and MFCUs already have NADAC. The reason they can't stop this fraud is not that they
  don't know wholesale insulin is $5.

---

## 7. What would actually catch the dominant fraud

Rank-ordered by signal strength for the fraud that dominates dollars:

1. **Ownership-graph analysis.** Ingest the new CMS ownership disclosures + state
   corporate filings (OpenCorporates) + bankruptcy dockets. Flag SNFs where >X% of
   operating cost goes to entities with ≥5% common ownership. This is the Grabowski/Mor
   "Where Does the Money Go?" approach — fully replicable from public data. **Best hackathon-feasible option.**
2. **Cost-report related-party-markup detector.** For every SNF, pull HCRIS. Compute
   related-party line costs vs. the non-related-party peer median per bed-day for the
   same state and case mix. Flag z-score outliers. Completely public data.
3. **Acuity vs. staffing divergence (PBJ × MDS).** Facility claims PDPM NTA Tier A
   (high-acuity, extensive services) but PBJ shows below-median RN hours/resident/day →
   either the acuity is upcoded or the care isn't being delivered. OIG already does a
   version; a public dashboard is novel.
4. **Resident/family attestation of services delivered.** QR-code on the resident's
   wristband → "did you receive PT today? Did you get your insulin?" — matched against
   the MDS Section O therapy minutes and Section N medications. Catches **(c) quantity**
   and **(d) phantom-delivery** fraud. Hard to get resident cooperation but demos well.
5. **Reference-price comparison (what the team was going to build):** marginal value.
   Only works on Part B J-codes and Part D — a small slice — and CMS already does it.

### Recommended 6-hour demo

**Build #1 + a thin slice of #2 and present it as "Nursing Home Money Trail."**

- Pull one state's HCRIS cost reports (CSV, ~500MB) → for each SNF extract total
  operating cost, related-party cost, PBJ staffing hours, star rating, ownership chain.
- Join to CMS Ownership file → render the graph (D3/networkx + pyvis).
- For each facility compute: **"% of Medicaid dollars flowing to related parties"** and
  **"staffing-adjusted overcharge estimate."**
- Demo narrative: *"CMS says this home charges Medicaid $340/day. $190 of that goes to
  companies owned by the same two people who own the home. Here's the graph. Here's
  the three other homes they own doing the same thing. The $45 insulin markup you were
  going to catch with a price scraper — that's where it actually lives."*

That beats a price-scraper demo on substance **and** is directly grounded in the
documented fraud pattern.

---

## Source pointers (verify URLs — many DOJ paths moved in May 2025 restructuring)

- DOJ press releases: search `site:justice.gov "nursing" settle` or use
  justice.gov/opa/press-releases search.
- OIG report **OEI-02-20-00490** on SNF related-party disclosures (PDF resolves at
  `https://oig.hhs.gov/oei/reports/oei-02-20-00490.pdf`).
- NBER **w28474** Gupta/Howell/Yannelis/Gurun — PE and nursing-home mortality/tunneling.
- Grabowski, Stevenson, Mor — "Private Equity Ownership of Nursing Homes: Implications
  for Residents and Workforce" (Health Affairs 2021, 2023 follow-up).
- NYT "Maggots, Rape and Yet Five Stars" (Mar 13 2021); "Phantom Nurses" (Sep 11 2022).
- ProPublica "When Private Equity Takes Over a Nursing Home" (series, 2020–2023).
- GAO **GAO-23-105533** "Nursing Home Oversight."
- CMS SNF PPS PDPM rules at cms.gov/medicare/payment/prospective-payment-systems/skilled-nursing-facility-snf.
- HCRIS cost reports: cms.gov → Research-Statistics-Data-and-Systems → Cost Reports → SNF-2540.
- Nursing Home Ownership rule (Nov 2023, 42 CFR 424.516): ownership data at data.cms.gov.
