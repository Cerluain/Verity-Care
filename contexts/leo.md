# System Design Document: Elder Care Fraud Prevention & Service Verification Architecture

## 1. Executive Summary

Government-funded elder care (Medicare, Medicare Advantage, and state Medicaid programs such as Arizona's AHCCCS/ALTCS) suffers from three distinct, high-impact fraud and financial abuse vectors:

1. **Ghost Jobs & Phantom Staffing:** Facilities falsify Payroll-Based Journal (PBJ) hours or use "tap-and-leave" tactics to inflate CMS Five-Star ratings and meet minimum staffing mandates while leaving care floors dangerously understaffed.
2. **Related-Party Cost Markups:** Parent corporations tunnel roughly 63% to 68% of true facility profits into affiliated shell LLCs (real estate, management, medical supplies) at inflated transfer prices, making facilities appear unprofitable on cost reports to lobby for higher taxpayer reimbursement rates.
3. **Phantom Care & Undelivered Items:** Unbundled ancillary providers (Durable Medical Equipment suppliers, visiting therapists, mobile clinics, and home health agencies) bill Medicare/Medicaid for items and visits never delivered to beneficiaries.

Current oversight relies on **post-hoc self-reported filings** and understaffed reactive audits. This design document outlines a modular verification architecture combining **Zero-Knowledge Proofs (ZKPs)**, **hardware-anchored mobile credentials**, **automated benchmark pricing**, and **targeted proxy/beneficiary verification**—retaining only the mechanisms that score average or higher on operational usability, data reliability, privacy preservation, and regulatory feasibility.

---

## 2. Solution Filtering & Viability Matrix

Before detailing the system architecture, lower-viability concepts explored during discovery were filtered out in favor of higher-leverage approaches:

| Fraud Domain | Discarded / Low-Viability Approaches | Retained Approaches (Average to High Viability) | Rationale for Selection |
| :--- | :--- | :--- | :--- |
| **Ghost Staffing** | Legacy 125kHz physical RFID badges; unanchored timeclock apps | **Hardware-Anchored Mobile NFC + ZK-Staffing Proofs** | Physical cards are trivially shared or cloned; smartphone Secure Elements + biometric checks + multi-zone door anchors bind presence to a licensed human without mass surveillance. |
| **Cost Markups** | Manual line-item audits of shell LLC ownership trees; forced public disclosure of raw vendor contracts | **1. GPO Reference Pricing Caps**<br>**2. Signed E-Invoicing + ZK Markup/Ownership Proofs**<br>**3. Consolidated GAAP Reporting (Corporate Chains)** | Reference caps eliminate shell-company incentives with zero operator friction; ZK e-invoices prove cost integrity while protecting proprietary supplier trade secrets. |
| **Phantom Care** | Direct cold-calling of nursing home residents inside SNFs | **1. Healthcare Proxy / POA EOB Alerting (Blue Button 2.0)**<br>**2. Direct Post-Visit Verification for Home Health / HCBS**<br>**3. B2B Rogue-Vendor Shield for Payers & SNFs** | ~42%–58% of SNF residents have dementia/cognitive impairment and lack personal phones. Routing SNF alerts to Healthcare Proxies and focusing direct calls on independent Home Health patients solves data noise and retaliation risks. |

---

## 3. Module A: Verifiable Staffing & Anti-Ghost-Job Protocol

### 3.1 Objective
Mathematically prove that a nursing facility met mandated caregiver-to-resident staffing ratios with active, state-licensed staff physically working across the building—without exposing employee Personally Identifiable Information (PII), schedules, wages, or HIPAA-protected resident records.

### 3.2 Core Components
1. **Credential Issuer (State Licensing Board / Identity Verifier):**
   * Performs a one-time verification of the worker's government ID and active clinical license (RN, LPN, CNA).
   * Issues a blind signature or **BBS+ Verifiable Credential** bound to a non-exportable keypair generated inside the employee's smartphone **Secure Element / Trusted Execution Environment (TEE)**.
2. **Hardware Anchors (Existing Facility NFC Readers):**
   * Leverages existing contactless readers on medication rooms, supply closets, staff breakrooms, and memory-care wing doors.
   * Each reader holds an embedded cryptographic signing key and executes a challenge-response handshake with the employee's phone during normal workflow taps.
3. **Biometric Liveness Gate:**
   * Unlocking the mobile NFC credential requires local device biometric authentication (FaceID/fingerprint), preventing managers from hoarding physical cards or carrying multiple unlocked phones for absent workers.
4. **ZK Prover & Verifier Circuit (Noir / Circom):**
   * At the end of each shift, the facility's local server ingests hardware-signed tap logs as **private witnesses** and generates a succinct proof (`VALID` / `INVALID`) submitted to regulators or CMS PBJ portals.

### 3.3 Zero-Knowledge Circuit Constraints
For a shift window $S$ and active resident census $C$, the circuit enforces four simultaneous constraints:

1. **Credential & Hardware Authenticity:** Every clock-in, zone tap, and clock-out signature traces back to an unrevoked state caregiver credential and a registered facility door reader.
2. **Epoch Nullifier Uniqueness (Anti-Double-Counting):** Each worker deterministically derives a shift nullifier:
   $$\text{Nullifier}_i = \text{Hash}(\text{sk}_i, \text{Date}, \text{ShiftID})$$
   The circuit enforces $\text{Nullifier}_i \neq \text{Nullifier}_j$ for all $i \neq j$, preventing a single credential from being counted twice in one facility or concurrently across two facilities.
3. **Minimum Shift Duration & Spatial-Temporal Liveness:**
   * Total shift duration meets required minimums:
     $$T_{\text{out}, i} - T_{\text{in}, i} \ge H_{\min}$$
   * **Multi-Zone Trajectory:** The worker must record authenticated taps across at least $k$ distinct building zones (e.g., Wing A Med Room, Central Station, Supply Closet) distributed across the shift.
   * **Impossible-Travel Bound:** Consecutive taps by worker $i$ at doors $A$ and $B$ must obey physical walking speed limits:
     $$\frac{d(\text{Door}_A, \text{Door}_B)}{t_B - t_A} \le v_{\max}$$
4. **Staffing Ratio Compliance:** The count of verified active workers $N_{\text{valid}}$ satisfies the mandated clinical ratio $R(C)$ for the daily resident census:
   $$N_{\text{valid}} \ge R(C)$$

### 3.4 Usability & Feasibility Assessment
* **Operator & Staff Friction:** **Low.** Nurses already tap into medication rooms and restricted wings dozens of times per shift; replacing legacy plastic badges with Apple/Google Wallet NFC credentials streamlines access while generating cryptographic proofs passively.
* **Privacy:** **Strict Zero-Knowledge.** Regulators verify aggregate staffing compliance; employee identities and movement trails never leave the facility's local proving environment.

---

## 4. Module B: Anti-Markup & Cost-Reporting Integrity Layer

### 4.1 Objective
Prevent nursing home operators from inflating supply and service expenses through related-party shell LLCs without requiring auditors to manually untangle multi-state corporate ownership trees.

### 4.2 Dual-Track Solution Architecture

#### Track B1: Automated GPO Reference Pricing Caps (Commodities & Standard Supplies)
* **Mechanism:** Rather than auditing vendor ownership for standardized goods (gloves, wound dressings, incontinence supplies, nutritional supplements), regulators link cost-report reimbursement ceilings directly to public **Group Purchasing Organization (GPO)** fair-market unit price indexes (enforcing Medicare's existing "Prudent Buyer" rule under 42 CFR 413.17).
* **Rule:** If a facility buys bandages from an affiliated LLC at $50/box when the GPO benchmark cap is $5/box, the $45 markup is automatically disallowed from cost-report rate calculations.
* **Usability & Legal Feasibility:** **Highest.** Adds zero administrative burden to honest operators and requires no new statutory authority—only routine index updates by CMS or state Medicaid agencies.

#### Track B2: Signed E-Invoicing + ZKP Markup & Ownership Proofs (Wholesalers & Contracts)
* **Mechanism:** Primary manufacturers and wholesale distributors issue cryptographically signed electronic invoices (via EDI/Peppol standards) containing item SKU, quantity, unit price, and a hashed beneficial-ownership tree commitment.
* **ZK Compliance Proof:** When filing annual cost reports, the facility's accounting/ERP software (e.g., PointClickCare, NetSuite) generates a ZK proof verifying:
  1. **Zero Intercompany Markup:** The expense claimed on the cost report equals the original primary supplier's signed invoice amount ($P_{\text{claimed}} \le P_{\text{invoice}}$).
  2. **Ownership Disjointness (Non-Membership Proof):** The cryptographic hash set of the vendor's beneficial owners shares zero intersection with the nursing home's ownership tree ($\text{Owners}_{\text{facility}} \cap \text{Owners}_{\text{vendor}} = \emptyset$), or any shared ownership has automatically triggered a downward cost-basis adjustment.
* **Usability & Legal Feasibility:** **Moderate-to-High.** Eliminates the industry's primary legal objection to transparency—protecting proprietary bulk discounts and supplier contracts as trade secrets—making it ideal as a voluntary "audit safe harbor" for state Medicaid programs.

#### Track B3: Consolidated GAAP Financials (Multi-Facility Chains)
* **Mechanism:** Require multi-entity corporate operators and private equity groups controlling both facilities and vendors to submit audited, consolidated GAAP financial statements (modeled on Illinois transparency statutes) that automatically eliminate intercompany transfer profits.

---

## 5. Module C: Phantom Care & Unbundled Billing Verification Engine

### 5.1 Objective
Detect and block fraudulent claims for undelivered medical equipment, therapy sessions, and clinical visits before taxpayer funds are paid out—without relying on unreliable cold calls to cognitively impaired nursing home residents.

### 5.2 Three High-Viability Product Pillars

#### Pillar C1: Healthcare Proxy / POA EOB Alerting (For SNF Residents)
* **Data Ingestion:** Integrates with **CMS Blue Button 2.0 APIs**, Medicare Summary Notices (MSNs), or Medicare Advantage Explanation of Benefits (EOB) feeds with beneficiary/proxy consent.
* **Anomaly Triggering:** Flags high-risk unbundled Part B and DMEPOS claims billed on top of a resident's daily SNF rate—specifically orthotic braces, custom wheelchairs, surgical wound dressings, mobile imaging, and high-frequency therapy sessions.
* **Verification Workflow:** Instead of calling the resident inside the facility, the system sends an automated SMS or plain-language voice prompt to the resident's **designated Healthcare Proxy / Power of Attorney**:
  > *"Medicare was billed $650 by [Vendor Name] for a knee brace and 4 physical therapy visits for [Resident Name] this week. Reply YES to confirm receipt or NO to flag for review."*
* **Impact:** Bypasses dementia-related recall errors, avoids resident fear of staff retaliation, and leverages family caregivers who actively scrutinize bills.

#### Pillar C2: Direct Recipient Verification for Home Health & Medicaid HCBS
* **Target Market:** In-home nursing, physical therapy, and Medicaid Home and Community-Based Services (HCBS) personal care agencies.
* **Why It Works Here:** Unlike SNF residents, home-care beneficiaries live independently, possess personal mobile phones, and receive care billed strictly per visit or per hour.
* **Verification Workflow:** Following Electronic Visit Verification (EVV) check-out, the platform triggers an automated post-visit SMS or interactive voice call directly to the patient confirming caregiver arrival, duration, and services rendered, routing mismatches directly to payer Special Investigations Units (SIUs).

#### Pillar C3: Pre-Payment Rogue-Vendor Shield (B2B Payer & SNF SaaS)
* **Mechanism:** Nursing homes are frequently targeted by outside fraudulent DME suppliers and labs that obtain resident Medicare numbers and submit phantom claims without facility authorization.
* **Workflow:** Cross-references incoming Part B / DMEPOS claims against the nursing home's internal clinical orders and approved vendor whitelist prior to claim settlement. If an unapproved outside supplier bills for supplies not ordered by the facility's medical director, the claim is auto-held for payer review.

---

## 6. Phased Implementation & Go-To-Market Roadmap

Because deploying hardware-anchored ZKPs requires institutional adoption while proxy/payer verification can launch immediately via software APIs, the system is designed for phased rollout:

| Phase | Target Modules | Primary Customer / Partner | Key Deliverable & Value Proposition |
| :--- | :--- | :--- | :--- |
| **Phase 1 (Months 1–4)**<br>*Immediate Software MVP* | **Module C (Pillars C1, C2, C3):** Proxy EOB Alerting & Home Health Verification | Medicare Advantage Plans, Medicaid Managed Care Organizations (MCOs), & Compliant SNF Chains | API-driven claim verification engine that stops phantom DMEPOS and home-health payouts pre-settlement, delivering immediate ROI to insurers. |
| **Phase 2 (Months 5–9)**<br>*Financial Integrity Layer* | **Module B (Tracks B1 & B2):** GPO Benchmark Engine + ERP E-Invoice ZK Plugin | State Medicaid Agencies (e.g., AHCCCS) & Healthcare ERP Vendors | Automated cost-report screening tool flagging above-benchmark supply markups and offering cryptographic audit safe harbors for compliant facilities. |
| **Phase 3 (Months 10–18)**<br>*Cryptographic Floor Verification* | **Module A:** Mobile NFC + Hardware-Anchored ZK-Staffing Pilot | Forward-Looking SNF Operators, State Nursing Boards, & CMS Innovation Center | Pilot deployment replacing legacy badge timeclocks with biometric mobile NFC and ZK shift proofs to automate PBJ staffing compliance. |