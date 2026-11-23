"""Generate the authored (demo_grounded) SPEND data from a few per-facility knobs.

Writes, under data/spend/:
  census.json            resident-days per facility (placeholder until Leo's PBJ numbers)
  ownership-graphs.json  facility -> operator -> parent, plus supplier ownership
  line-items.json        12 supplier->facility invoice rows per facility, Q3 2026

Quantities are derived from census x usage assumptions x a volume multiplier, and unit
prices from real NADAC x a price multiplier, so every number is internally consistent.
Re-run after changing a knob:  python scripts/build_demo_data.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
DATA = REPO / "data"
SPEND = DATA / "spend"
QUARTER_DAYS = 91  # Q3 2026: Jul 1 – Sep 30

# --------------------------------------------------------------------------------------
# Usage assumptions: share of residents on the drug, invoice units per user per day.
# Planning assumptions for the demo (not a cited clinical source) — returned in evidence.
# --------------------------------------------------------------------------------------
USAGE = {
    "insulin-lispro-vial": (0.12, 0.04),   # ~40 U/day from a 1,000 U vial
    "eliquis-5": (0.10, 2),
    "jardiance-10": (0.06, 1),
    "januvia-100": (0.06, 1),
    "xarelto-20": (0.04, 1),
    "enoxaparin-40": (0.03, 1),
    "metformin-500": (0.12, 2),
    "atorvastatin-40": (0.35, 1),
    "lisinopril-10": (0.20, 1),
    "amlodipine-5": (0.25, 1),
    "omeprazole-20": (0.30, 1),
    "furosemide-40": (0.20, 1),
    "levothyroxine-50": (0.18, 1),
    "gabapentin-300": (0.15, 3),
    "sertraline-50": (0.20, 1),
    "donepezil-10": (0.20, 1),
    "memantine-10": (0.12, 2),
    "tamsulosin-04": (0.08, 1),
    "quetiapine-25": (0.15, 1),
    "acetaminophen-325": (0.50, 4),
}

# Neutral wholesaler used by facilities with no related-party supplier.
WHOLESALER = "national-wholesaler"

# --------------------------------------------------------------------------------------
# Per-facility knobs. Each line: (drug_id, price_multiplier_vs_NADAC, volume_multiplier, supplier_node)
# --------------------------------------------------------------------------------------
FACILITIES = {
    "buffalo-center-centers-health": {
        "occupancy": 0.90,
        "lines": [
            ("insulin-lispro-vial", 4.2, 2.9, "empire-clinical-supply"),
            ("eliquis-5", 4.1, 1.3, "empire-clinical-supply"),
            ("jardiance-10", 3.6, 1.1, "empire-clinical-supply"),
            ("atorvastatin-40", 1.10, 0.90, "northeast-wholesale"),
            ("lisinopril-10", 1.05, 0.85, "northeast-wholesale"),
            ("amlodipine-5", 1.20, 0.95, "northeast-wholesale"),
            ("omeprazole-20", 1.15, 0.90, "northeast-wholesale"),
            ("furosemide-40", 0.95, 0.80, "northeast-wholesale"),
            ("levothyroxine-50", 1.10, 0.90, "northeast-wholesale"),
            ("sertraline-50", 1.25, 0.85, "northeast-wholesale"),
            ("donepezil-10", 1.05, 0.90, "northeast-wholesale"),
            ("acetaminophen-325", 1.00, 0.95, "northeast-wholesale"),
        ],
    },
    "accordius-rose-manor-portopiccolo": {
        "occupancy": 0.88,
        "lines": [
            ("quetiapine-25", 4.5, 2.4, "carolina-senior-rx"),
            ("eliquis-5", 3.4, 2.1, "carolina-senior-rx"),
            ("xarelto-20", 3.2, 1.6, "carolina-senior-rx"),
            ("memantine-10", 2.2, 1.3, "carolina-senior-rx"),
            ("donepezil-10", 1.30, 1.00, "carolina-senior-rx"),
            ("sertraline-50", 1.35, 0.95, "carolina-senior-rx"),
            ("gabapentin-300", 1.20, 0.90, "carolina-senior-rx"),
            ("omeprazole-20", 1.10, 0.90, "carolina-senior-rx"),
            ("atorvastatin-40", 1.15, 0.85, "carolina-senior-rx"),
            ("metformin-500", 1.05, 0.90, "carolina-senior-rx"),
            ("furosemide-40", 1.00, 0.85, "carolina-senior-rx"),
            ("acetaminophen-325", 1.10, 0.95, "carolina-senior-rx"),
        ],
    },
    "mi-casa-life-care-az": {
        "occupancy": 0.86,
        "lines": [
            ("januvia-100", 1.6, 1.0, "desert-sw-pharmacy"),
            ("insulin-lispro-vial", 1.15, 0.95, "desert-sw-pharmacy"),
            ("eliquis-5", 1.10, 0.90, "desert-sw-pharmacy"),
            ("metformin-500", 1.05, 0.90, "desert-sw-pharmacy"),
            ("atorvastatin-40", 1.10, 0.85, "desert-sw-pharmacy"),
            ("lisinopril-10", 1.00, 0.90, "desert-sw-pharmacy"),
            ("amlodipine-5", 1.05, 0.85, "desert-sw-pharmacy"),
            ("omeprazole-20", 1.10, 0.90, "desert-sw-pharmacy"),
            ("gabapentin-300", 1.15, 0.95, "desert-sw-pharmacy"),
            ("donepezil-10", 1.00, 0.90, "desert-sw-pharmacy"),
            ("tamsulosin-04", 1.10, 0.85, "desert-sw-pharmacy"),
            ("acetaminophen-325", 1.00, 0.95, "desert-sw-pharmacy"),
        ],
    },
    "crook-county-wy-rural": {
        "occupancy": 0.85,
        "lines": [
            ("insulin-lispro-vial", 3.2, 1.0, "high-plains-medical"),   # +220%: thin frontier market
            ("enoxaparin-40", 2.8, 0.9, "high-plains-medical"),         # +180%
            ("eliquis-5", 1.25, 0.9, "high-plains-medical"),
            ("metformin-500", 1.20, 0.9, "high-plains-medical"),
            ("atorvastatin-40", 1.30, 0.85, "high-plains-medical"),
            ("lisinopril-10", 1.25, 0.9, "high-plains-medical"),
            ("amlodipine-5", 1.20, 0.85, "high-plains-medical"),
            ("furosemide-40", 1.30, 0.9, "high-plains-medical"),
            ("levothyroxine-50", 1.20, 0.9, "high-plains-medical"),
            ("donepezil-10", 1.25, 0.85, "high-plains-medical"),
            ("omeprazole-20", 1.20, 0.9, "high-plains-medical"),
            ("acetaminophen-325", 1.15, 0.95, "high-plains-medical"),
        ],
    },
    "terraces-phoenix-humangood": {
        "occupancy": 0.92,
        "lines": [
            ("eliquis-5", 1.05, 0.90, WHOLESALER),
            ("jardiance-10", 1.10, 0.85, WHOLESALER),
            ("atorvastatin-40", 1.00, 0.90, WHOLESALER),
            ("lisinopril-10", 0.95, 0.85, WHOLESALER),
            ("amlodipine-5", 1.05, 0.90, WHOLESALER),
            ("omeprazole-20", 1.10, 0.85, WHOLESALER),
            ("levothyroxine-50", 1.00, 0.90, WHOLESALER),
            ("sertraline-50", 1.05, 0.80, WHOLESALER),
            ("donepezil-10", 1.10, 0.90, WHOLESALER),
            ("memantine-10", 1.00, 0.85, WHOLESALER),
            ("tamsulosin-04", 1.05, 0.90, WHOLESALER),
            ("acetaminophen-325", 0.95, 0.90, WHOLESALER),
        ],
    },
    "haven-health-green-valley": {
        "occupancy": 0.89,
        "lines": [
            ("insulin-lispro-vial", 1.10, 0.90, WHOLESALER),
            ("eliquis-5", 1.05, 0.85, WHOLESALER),
            ("januvia-100", 1.00, 0.90, WHOLESALER),
            ("metformin-500", 1.10, 0.90, WHOLESALER),
            ("atorvastatin-40", 1.05, 0.85, WHOLESALER),
            ("amlodipine-5", 1.00, 0.90, WHOLESALER),
            ("omeprazole-20", 1.15, 0.90, WHOLESALER),
            ("furosemide-40", 1.05, 0.85, WHOLESALER),
            ("gabapentin-300", 1.10, 0.90, WHOLESALER),
            ("quetiapine-25", 1.00, 0.80, WHOLESALER),
            ("sertraline-50", 1.05, 0.85, WHOLESALER),
            ("acetaminophen-325", 1.00, 0.90, WHOLESALER),
        ],
    },
}

# --------------------------------------------------------------------------------------
# Ownership graphs. Real parent companies come from data/facilities.json citations.
# Vendor/supplier entities are ILLUSTRATIVE (fictional names), flagged illustrative=True.
# --------------------------------------------------------------------------------------
def node(id_, label, type_, illustrative=False, **details):
    return {"id": id_, "label": label, "type": type_, "illustrative": illustrative, "details": details}


def owned_by(child, parent, label="owned by"):
    return {"from": child, "to": parent, "type": "owned_by", "label": label}


DE_AGENT = node("agent-dover-de", "Registered agent — Dover, DE", "registered_agent", True,
                note="Shared registered agent (illustrative)")

GRAPHS = {
    "buffalo-center-centers-health": {
        "nodes": [
            node("buffalo-center-centers-health", "Buffalo Center for Rehabilitation and Nursing", "facility", state="NY"),
            node("delaware-operations-assoc", "Delaware Operations Assoc LLC", "operator", state="NY",
                 note="Operating entity named in facilities.json"),
            node("centers-health-care", "Centers Health Care", "parent", state="NY",
                 note="Parent named in NY AG lawsuit (Nov 2023)"),
            node("empire-clinical-supply", "Empire Clinical Supply LLC", "supplier", True, state="DE",
                 note="Owner-controlled vendor (illustrative name; pattern per NY AG complaint)"),
            node("northeast-wholesale", "Northeast Wholesale Pharmacy Inc", "supplier", True, state="NY",
                 note="Independent wholesaler (illustrative)"),
            DE_AGENT,
        ],
        "edges": [
            owned_by("buffalo-center-centers-health", "delaware-operations-assoc", "operated by"),
            owned_by("delaware-operations-assoc", "centers-health-care"),
            owned_by("empire-clinical-supply", "centers-health-care"),
            {"from": "empire-clinical-supply", "to": "agent-dover-de", "type": "registered_agent", "label": "registered agent"},
            {"from": "delaware-operations-assoc", "to": "agent-dover-de", "type": "registered_agent", "label": "registered agent"},
        ],
        "notes": "Parent/operator from NY AG v. Centers Health Care (Nov 2023). Vendor LLC names are illustrative; "
                 "production pulls CMS ownership (PECOS) + state SOS filings.",
    },
    "accordius-rose-manor-portopiccolo": {
        "nodes": [
            node("accordius-rose-manor-portopiccolo", "Accordius Health at Rose Manor", "facility", state="NC"),
            node("accordius-health", "Accordius Health (operating brand)", "operator", state="NC"),
            node("portopiccolo-group", "Portopiccolo Group", "parent", state="NJ",
                 note="PE owner per ProPublica (Nov 2020)"),
            node("carolina-senior-rx", "Carolina Senior Rx LLC", "supplier", True, state="NC",
                 note="Captive LTC pharmacy (illustrative name; captive-vendor pattern per ProPublica)"),
        ],
        "edges": [
            owned_by("accordius-rose-manor-portopiccolo", "accordius-health", "operated by"),
            owned_by("accordius-health", "portopiccolo-group"),
            owned_by("carolina-senior-rx", "portopiccolo-group"),
        ],
        "notes": "Parent from ProPublica Portopiccolo reporting (Nov 2020). Pharmacy name is illustrative.",
    },
    "mi-casa-life-care-az": {
        "nodes": [
            node("mi-casa-life-care-az", "Mi Casa Nursing Center", "facility", state="AZ"),
            node("life-care-centers", "Life Care Centers of America", "parent", state="TN"),
            node("desert-sw-pharmacy", "Desert Southwest Pharmacy Services", "supplier", True, state="AZ",
                 note="Independent LTC pharmacy (illustrative)"),
            node("desert-sw-owner", "Independent owner", "parent", True, state="AZ"),
        ],
        "edges": [
            owned_by("mi-casa-life-care-az", "life-care-centers", "operated by"),
            owned_by("desert-sw-pharmacy", "desert-sw-owner"),
        ],
        "notes": "No common ownership between facility and supplier. Supplier name is illustrative.",
    },
    "crook-county-wy-rural": {
        "nodes": [
            node("crook-county-wy-rural", "Crook County Medical Services District LTC", "facility", state="WY"),
            node("crook-county-msd", "Crook County Medical Services District", "parent", state="WY",
                 note="County hospital district (non-profit)"),
            node("high-plains-medical", "High Plains Medical Distributors", "supplier", True, state="SD",
                 note="Regional distributor serving frontier WY (illustrative)"),
            node("high-plains-owner", "Independent owner", "parent", True, state="SD"),
        ],
        "edges": [
            owned_by("crook-county-wy-rural", "crook-county-msd", "operated by"),
            owned_by("high-plains-medical", "high-plains-owner"),
        ],
        "notes": "Public district owner; independent regional supplier. Thin frontier market explains high unit prices.",
    },
    "terraces-phoenix-humangood": {
        "nodes": [
            node("terraces-phoenix-humangood", "The Terraces of Phoenix", "facility", state="AZ"),
            node("humangood-az", "HumanGood Arizona Inc", "operator", state="AZ"),
            node("humangood", "HumanGood (non-profit)", "parent", state="CA"),
            node(WHOLESALER, "National drug wholesaler", "supplier", True, note="Generic national wholesaler (illustrative)"),
            node("wholesaler-public", "Publicly traded parent", "parent", True),
        ],
        "edges": [
            owned_by("terraces-phoenix-humangood", "humangood-az", "operated by"),
            owned_by("humangood-az", "humangood"),
            owned_by(WHOLESALER, "wholesaler-public"),
        ],
        "notes": "No common ownership between facility and supplier.",
    },
    "haven-health-green-valley": {
        "nodes": [
            node("haven-health-green-valley", "Haven Health Green Valley", "facility", state="AZ"),
            node("haven-health", "Haven Health (regional AZ chain)", "parent", state="AZ"),
            node(WHOLESALER, "National drug wholesaler", "supplier", True, note="Generic national wholesaler (illustrative)"),
            node("wholesaler-public", "Publicly traded parent", "parent", True),
        ],
        "edges": [
            owned_by("haven-health-green-valley", "haven-health", "operated by"),
            owned_by(WHOLESALER, "wholesaler-public"),
        ],
        "notes": "No common ownership between facility and supplier.",
    },
}

INVOICE_DATES = ["2026-07-08", "2026-07-22", "2026-08-05", "2026-08-19", "2026-09-02", "2026-09-16"]


def main() -> None:
    facilities = {f["id"]: f for f in json.loads((DATA / "facilities.json").read_text())}
    prices = json.loads((SPEND / "prices.json").read_text())["drugs"]

    assert set(FACILITIES) == set(facilities), "knob ids must match data/facilities.json"

    census, line_items = {}, {}
    for fid, cfg in FACILITIES.items():
        beds = facilities[fid]["beds"]
        residents = round(beds * cfg["occupancy"])
        rdays = residents * QUARTER_DAYS
        census[fid] = {
            "beds": beds,
            "occupancy": cfg["occupancy"],
            "avg_residents": residents,
            "resident_days_quarter": rdays,
            "quarter": "2026-Q3",
            "source": "placeholder: beds × occupancy × 91 days (swap for PBJ resident-days from Dev B)",
            "data_provenance": "demo_grounded",
        }
        rows = []
        for i, (drug, pmult, vmult, supplier) in enumerate(cfg["lines"], start=1):
            ref = prices[drug]["reference_price_per_invoice_unit"]
            share, per_day = USAGE[drug]
            expected = rdays * share * per_day
            qty = max(1, round(expected * vmult))
            unit_price = round(ref * pmult, 4)
            rows.append({
                "line_id": f"L{i:03d}",
                "invoice_no": f"INV-{fid[:4].upper()}-{2600 + i}",
                "invoice_date": INVOICE_DATES[(i - 1) % len(INVOICE_DATES)],
                "drug_id": drug,
                "drug": prices[drug]["name"],
                "ndc": prices[drug]["example_ndc"],
                "unit": prices[drug]["invoice_unit"],
                "qty": qty,
                "unit_price": unit_price,
                "total": round(unit_price * qty, 2),
                "supplier_id": supplier,
            })
        line_items[fid] = rows

    meta = {"data_provenance": "demo_grounded",
            "note": "Authored for the demo by scripts/build_demo_data.py. Reference prices are real (NADAC)."}
    (SPEND / "census.json").write_text(json.dumps({"_meta": {**meta, "usage_assumptions": {
        k: {"share_of_residents": s, "units_per_user_per_day": d} for k, (s, d) in USAGE.items()}},
        "facilities": census}, indent=2) + "\n")
    (SPEND / "line-items.json").write_text(json.dumps({"_meta": meta, "facilities": line_items}, indent=2) + "\n")
    (SPEND / "ownership-graphs.json").write_text(json.dumps({"_meta": meta, "facilities": GRAPHS}, indent=2) + "\n")
    print("wrote census.json, line-items.json, ownership-graphs.json")


if __name__ == "__main__":
    main()
