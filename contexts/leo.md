# System Design Document: Elder Care Integrity Platform (Hackathon MVP & Scale Roadmap)

## 1. Executive Summary

Government-funded elder care across Medicare, Medicare Advantage, and state Medicaid programs (such as Arizona's AHCCCS/ALTCS) suffers from three distinct, high-impact fraud and financial abuse vectors:

1. **Ghost Jobs & Phantom Staffing:** Facilities falsify Payroll-Based Journal (PBJ) hours or use "tap-and-leave" badge schemes to inflate CMS Five-Star ratings and satisfy minimum staffing mandates while leaving care floors dangerously understaffed.
2. **Related-Party Cost Markups:** Parent organizations tunnel an estimated 63% to 68% of true facility profits into affiliated shell LLCs (real estate, management, therapy, medical supplies) via inflated transfer prices, making facilities appear unprofitable on cost reports to lobby for higher reimbursement rates.
3. **Phantom Care & Undelivered Items:** Unbundled ancillary providers (Durable Medical Equipment suppliers, visiting therapists, mobile clinics, and home health agencies) bill Medicare or Medicaid for items and visits never delivered to beneficiaries.

Current oversight relies on **post-hoc self-reported filings** and understaffed reactive audits. This design document defines a unified **Eldercare Integrity Platform** built around a 7-hour hackathon MVP architecture and a phased commercial rollout, retaining only mechanisms that score average or higher on operational usability, data reliability, privacy preservation, and legal feasibility.

---

## 2. Solution Filtering & Viability Matrix

Lower-viability concepts identified during discovery were filtered out in favor of mechanisms with higher data reliability and lower deployment friction:

| Fraud Domain | Discarded / Low-Viability Approaches | Retained High-Viability Approaches | Core Design Rationale |
| :--- | :--- | :--- | :--- |
| **Ghost Jobs & Staffing** | Physical RFID keycards (easily cloned or left at the front desk for managers to tap); raw GPS/camera employee surveillance (violates worker privacy and faces union pushback). | **Hardware-Anchored Mobile NFC + Zero-Knowledge Proofs (ZKPs):** Smartphone Secure Enclave keys paired with biometric unlock, multi-zone door taps, and Poseidon nullifiers. | Proves distinct licensed staff worked full shifts across multiple building zones without exposing employee PII, wages, or exact movement trails. |
| **Related-Party Cost Markups** | Manual forensic audits of every sister LLC's private tax returns; requiring small independent homes to overhaul accounting systems overnight. | **GPO Reference-Pricing Caps + Beneficial Ownership Cross-Referencing:** Capping allowable supply costs at Group Purchasing Organization (GPO) benchmarks and flagging shared LLC owners/registered agents. | Uses existing CMS "Prudent Buyer" legal authority (42 CFR 413.17) to disallow markups automatically without needing access to shell company bank accounts. |
| **Phantom Care & Undelivered Items** | Calling nursing home residents directly (42% to 58% have dementia/cognitive impairment, lack personal phones, or fear staff retaliation). | **Healthcare Proxy / Family POA Verification + Home Health Targeting:** Automated SMS/voice checks sent to the resident's designated Healthcare Proxy triggered by high-risk Medicare Part B / DMEPOS claims. | Family caregivers review bills without cognitive barriers or fear of retaliation; direct beneficiary calls are reserved for cognitively independent in-home care recipients. |

---

## 3. Hackathon MVP Architecture (7-Hour Sprint Scope)

For the 12-hour hackathon demo, all three tracks integrate into a single **Eldercare Integrity Dashboard** monitoring a simulated facility (**Sunset Pines Care Facility #402**, 30 residents, minimum requirement of 5 licensed nurses per shift).

```
+-----------------------------------------------------------------------------------+
|                        ELDERCARE INTEGRITY DASHBOARD (React)                      |
|  [ Tab 1: Floor ZKP Staffing ]   [ Tab 2: Family Proxy ]   [ Tab 3: Cost X-Ray ]  |
+----------------+-----------------------------+------------------------------------+
                 |                             |
     +-----------v-----------+     +-----------v-----------+     +------------------+
     |   Noir / Barretenberg |     |  Twilio SMS / Voice   |     |  GPO Benchmark & |
     |   ZK Prover & Verifier|     |  Webhook Engine       |     |  LLC Graph Engine|
     +-----------------------+     +-----------------------+     +------------------+
```

### Track 1: Ghost-Job ZKP Verification Pipeline (Primary Cryptographic Engine)
* **Stack:** Noir (`nargo`) + Barretenberg (`bb`) backend wrapped in a lightweight FastAPI endpoint (or `@noir-lang/noir_js` WASM), connected to a split-screen React UI.
* **Circuit Inputs (`main.nr`):**
  * **Private Witnesses (Never leave facility machine):**
    * `worker_secrets: [Field; 5]` (simulated smartphone Secure Enclave keys)
    * `door_ids: [[Field; 2]; 5]` (NFC hardware anchor IDs tapped during shift)
    * `timestamps: [[u64; 2]; 5]` (Unix timestamps of start and mid/end taps)
  * **Public Inputs (Visible to State Auditor):**
    * `shift_id: pub Field`
    * `min_shift_seconds: pub u64` (e.g., `25200` seconds for 7 hours)
    * `claimed_nullifiers: pub [Field; 5]`
* **Circuit Constraints:**
  1. **Cryptographic Uniqueness (Anti-Double-Counting):** For each nurse $i \in \{0..4\}$, verify $\text{claimed\_nullifiers}[i] = \text{Poseidon}(\text{worker\_secrets}[i], \text{shift\_id})$, and assert $\text{claimed\_nullifiers}[i] \neq \text{claimed\_nullifiers}[j]$ for all $i \neq j$.
  2. **Spatial Liveness (Anti-Front-Desk Tap):** Assert $\text{door\_ids}[i][0] \neq \text{door\_ids}[i][1]$, proving each worker authenticated across at least two physically separate building zones (e.g., `Wing_A_MedRoom` and `Wing_B_Station`).
  3. **Temporal Shift Duration:** Assert $\text{timestamps}[i][1] > \text{timestamps}[i][0]$ and $(\text{timestamps}[i][1] - \text{timestamps}[i][0]) \ge \text{min\_shift\_seconds}$.
* **Demo UX (Split-Screen View):**
  * **Left Panel (Facility Local Machine — Private):** Displays raw nurse names, badge IDs, and door tap logs with two one-click presets: `Load Valid Shift (5 Active Nurses)` and `Load Ghost-Job Fraud (Cloned Front-Desk Taps)`.
  * **Right Panel (Regulator Auditor Portal — Public):** Displays *only* the cryptographic proof bytes, anonymous nullifier hashes, and a `VERIFIED` or `REJECTED` compliance status—demonstrating zero PII leakage.

### Track 2: Family Proxy Verification Engine (Phantom Care)
* **Stack:** Synthetic CMS Blue Button 2.0 FHIR `ExplanationOfBenefit` JSON + Node/Python backend + Twilio SMS/Voice API.
* **Workflow:**
  1. Ingest a resident's recent unbundled Medicare Part B / DMEPOS claims (e.g., `$650` knee orthotic brace, `4x` outpatient physical therapy visits).
  2. Rules engine flags high-fraud-risk HCPCS codes and dispatches an automated SMS or voice call to the registered Healthcare Proxy / Power of Attorney.
  3. When the proxy replies `NO` (or presses `2` on a voice call), a webhook updates the dashboard status from `Pending Verification` to `Disputed by Family Proxy` and freezes claim payout simulation.

### Track 3: Related-Party Cost-Report X-Ray (LLC Markup Detector)
* **Stack:** Python (`pandas` / FastAPI) or client-side TypeScript CSV/JSON analyzer.
* **Workflow:**
  1. Ingest a mock facility expense CSV (`vendor_name`, `item_category`, `unit_price`, `total_billed`) alongside a corporate entity registry JSON (modeled on CMS Additional Disclosable Party / PECOS filings).
  2. Cross-reference every line item against a **GPO Fair-Market Benchmark Table** to compute excess markup deltas above open-market rates.
  3. Perform an entity-resolution check matching shared parent LLCs, registered agents, or business addresses between the facility and vendors, surfacing hidden profit tunneling on the dashboard.

---

## 4. 7-Hour Sprint Execution Plan

| Time Block | Track 1 (ZKP Ghost Jobs) | Track 2 (Family Proxy) | Track 3 (Markup Detector) |
| :--- | :--- | :--- | :--- |
| **Hours 1 – 2** | Install `noirup` & `bbup`; write `main.nr` assertions; test valid and ghost-fraud `Prover.toml` files via CLI. | Create synthetic FHIR `ExplanationOfBenefit` JSON; configure Twilio trial SMS/Voice webhook. | Build sample cost-report CSV, GPO benchmark JSON, and corporate ownership graph JSON. |
| **Hours 3 – 4** | Wrap `nargo execute` + `bb prove` + `bb verify` in FastAPI endpoint returning proof hex and verification status. | Build claim-flagging trigger and webhook listener that updates claim status on proxy reply. | Write comparison script flagging unit prices $> 15\%$ above GPO caps and shared LLC links. |
| **Hours 5 – 6** | Build Split-Screen Facility Private Log vs. Auditor Public ZKP Verifier UI with preset scenarios. | Build Claims Feed UI showing live SMS dispatch and real-time `Disputed` badge updates. | Build Cost-Report X-Ray table and summary KPI cards showing total hidden markup dollars. |
| **Hour 7** | Merge all three tabs into unified dashboard; freeze code 30 minutes early; rehearse 3-minute demo pitch. | Merge & pitch rehearsal. | Merge & pitch rehearsal. |

---

## 5. Post-Hackathon Scaling & Go-To-Market (GTM) Strategy

Because nursing home operators resist voluntary transparency tools, commercial rollout must sequence **payer-side products first** (requiring zero facility permission) before expanding into **facility-side cryptographic compliance**.

### Phase 1 (Months 1 – 3): Payer-Side Phantom Care Verification (Wedge Product)
* **Target Customers:** Medicare Advantage Special Needs Plans (Institutional SNPs) and state Medicaid Managed Care Organizations (MCOs).
* **Value Proposition:** Immediate hard-dollar ROI by intercepting fraudulent Part B DMEPOS, therapy, and home-health claims before reimbursement clears.
* **GTM Motion:** Pilot with a regional Medicare Advantage plan or Home & Community-Based Services (HCBS) network using retrospective claims data to prove recovered leakage, pricing on a shared-savings or per-member-per-month (PMPM) SaaS basis.

### Phase 2 (Months 4 – 9): Automated Cost-Report & Related-Party Analytics
* **Target Customers:** State Medicaid Agencies (e.g., Arizona AHCCCS), CMS Unified Program Integrity Contractors (UPICs), and state Attorneys General Medicaid Fraud Control Units (MFCUs).
* **Value Proposition:** Automates desk audits of annual cost reports (Form CMS-2540-24) by joining Secretary of State corporate registries, CMS PECOS ownership data, and GPO pricing benchmarks—turning weeks of manual forensic accounting into instant risk scores.

### Phase 3 (Months 10 – 18): Hardware-Anchored ZKP Staffing Attestation
* **Target Customers:** Enterprise senior-living operators seeking reputational differentiation, lower liability insurance premiums, and regulatory "Audit Safe Harbor" status, integrated via existing EHR and mobile access partners (e.g., PointClickCare, HID Mobile Access).
* **Scaling Architecture:**
  * Replace simulated taps with **Apple Wallet / Google Wallet NFC credentials** bound to state nursing board verifiable credentials (BBS+ signatures).
  * Batch shift proofs using recursive ZK rollups so a 200-facility chain can publish a single daily cryptographic compliance attestation on-chain or to a state Medicaid portal in milliseconds.
  * Partner with state Medicaid rate-setting bodies to offer streamlined audit status or quality-incentive bonuses for facilities submitting continuous ZKP staffing proofs.