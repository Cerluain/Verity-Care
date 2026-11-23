"""One-time pull of real reference drug prices for the SPEND pillar.

Source: CMS NADAC (National Average Drug Acquisition Cost) via the data.medicaid.gov
datastore API. Public, no key. Writes data/spend/prices.json.

For each drug we take the most recent effective_date in the dataset and the median
nadac_per_unit across all NDCs listed for that description on that date.

Usage:
    python scripts/pull_prices.py            # pull + write prices.json
    python scripts/pull_prices.py --probe    # just print what each pattern matches
"""

from __future__ import annotations

import json
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

REPO = Path(__file__).resolve().parents[3]
OUT = REPO / "data" / "spend" / "prices.json"

NADAC_DATASET_ID = "fbb83258-11c7-47f5-8b18-5f8e79f7e704"  # "NADAC 2026"
NADAC_QUERY = f"https://data.medicaid.gov/api/1/datastore/query/{NADAC_DATASET_ID}/0"
NADAC_SOURCE_URL = "https://data.medicaid.gov/dataset/fbb83258-11c7-47f5-8b18-5f8e79f7e704"

# drug_id -> (display name, exact NADAC ndc_description, invoice unit label, NADAC units per invoice unit)
DRUGS: dict[str, tuple[str, str, str, float]] = {
    "insulin-lispro-vial": ("Insulin lispro 100 U/mL, 10 mL vial", "INSULIN LISPRO 100 UNIT/ML VL", "vial", 10.0),
    "eliquis-5": ("Eliquis (apixaban) 5 mg tablet", "ELIQUIS 5 MG TABLET", "tablet", 1.0),
    "jardiance-10": ("Jardiance (empagliflozin) 10 mg tablet", "JARDIANCE 10 MG TABLET", "tablet", 1.0),
    "januvia-100": ("Januvia (sitagliptin) 100 mg tablet", "JANUVIA 100 MG TABLET", "tablet", 1.0),
    "xarelto-20": ("Xarelto (rivaroxaban) 20 mg tablet", "XARELTO 20 MG TABLET", "tablet", 1.0),
    "enoxaparin-40": ("Enoxaparin 40 mg/0.4 mL syringe", "ENOXAPARIN 40 MG/0.4 ML SYR", "syringe", 0.4),
    "metformin-500": ("Metformin 500 mg tablet", "METFORMIN HCL 500 MG TABLET", "tablet", 1.0),
    "atorvastatin-40": ("Atorvastatin 40 mg tablet", "ATORVASTATIN 40 MG TABLET", "tablet", 1.0),
    "lisinopril-10": ("Lisinopril 10 mg tablet", "LISINOPRIL 10 MG TABLET", "tablet", 1.0),
    "amlodipine-5": ("Amlodipine 5 mg tablet", "AMLODIPINE BESYLATE 5 MG TAB", "tablet", 1.0),
    "omeprazole-20": ("Omeprazole DR 20 mg capsule", "OMEPRAZOLE DR 20 MG CAPSULE", "capsule", 1.0),
    "furosemide-40": ("Furosemide 40 mg tablet", "FUROSEMIDE 40 MG TABLET", "tablet", 1.0),
    "levothyroxine-50": ("Levothyroxine 50 mcg tablet", "LEVOTHYROXINE 50 MCG TABLET", "tablet", 1.0),
    "gabapentin-300": ("Gabapentin 300 mg capsule", "GABAPENTIN 300 MG CAPSULE", "capsule", 1.0),
    "sertraline-50": ("Sertraline 50 mg tablet", "SERTRALINE HCL 50 MG TABLET", "tablet", 1.0),
    "donepezil-10": ("Donepezil 10 mg tablet", "DONEPEZIL HCL 10 MG TABLET", "tablet", 1.0),
    "memantine-10": ("Memantine 10 mg tablet", "MEMANTINE HCL 10 MG TABLET", "tablet", 1.0),
    "tamsulosin-04": ("Tamsulosin 0.4 mg capsule", "TAMSULOSIN HCL 0.4 MG CAPSULE", "capsule", 1.0),
    "quetiapine-25": ("Quetiapine 25 mg tablet", "QUETIAPINE FUMARATE 25 MG TAB", "tablet", 1.0),
    "acetaminophen-325": ("Acetaminophen 325 mg tablet", "ACETAMINOPHEN 325 MG TABLET", "tablet", 1.0),
}


def query(client: httpx.Client, description: str, operator: str = "=") -> list[dict]:
    params = {
        "conditions[0][property]": "ndc_description",
        "conditions[0][value]": description,
        "conditions[0][operator]": operator,
        "sorts[0][property]": "effective_date",
        "sorts[0][order]": "desc",
        "limit": 200,
    }
    r = client.get(NADAC_QUERY, params=params, timeout=60)
    r.raise_for_status()
    return r.json().get("results", [])


def summarise(rows: list[dict]) -> dict | None:
    if not rows:
        return None
    latest = max(r["effective_date"] for r in rows)
    at_latest = [r for r in rows if r["effective_date"] == latest]
    prices = [float(r["nadac_per_unit"]) for r in at_latest]
    return {
        "nadac_per_unit": round(statistics.median(prices), 5),
        "pricing_unit": at_latest[0]["pricing_unit"],
        "effective_date": latest,
        "example_ndc": at_latest[0]["ndc"],
        "ndc_count": len({r["ndc"] for r in at_latest}),
    }


def main() -> int:
    probe = "--probe" in sys.argv
    out: dict[str, dict] = {}
    missing: list[str] = []
    with httpx.Client() as client:
        for drug_id, (name, desc, unit, factor) in DRUGS.items():
            rows = query(client, desc)
            s = summarise(rows)
            if probe:
                if s:
                    print(f"OK   {drug_id:22} {desc:38} ${s['nadac_per_unit']}/{s['pricing_unit']} ({s['effective_date']}, {s['ndc_count']} NDCs)")
                else:
                    near = query(client, f"%{desc.split()[0]}%", "LIKE")
                    names = sorted({r['ndc_description'] for r in near})[:8]
                    print(f"MISS {drug_id:22} {desc:38} near: {names}")
                continue
            if not s:
                missing.append(drug_id)
                continue
            out[drug_id] = {
                "name": name,
                "nadac_description": desc,
                "invoice_unit": unit,
                "nadac_units_per_invoice_unit": factor,
                "reference_price_per_invoice_unit": round(s["nadac_per_unit"] * factor, 4),
                **s,
                "source": "CMS NADAC (National Average Drug Acquisition Cost) 2026",
                "source_url": NADAC_SOURCE_URL,
            }
    if probe:
        return 0
    if missing:
        print(f"ERROR: no NADAC rows for {missing}", file=sys.stderr)
        return 1
    OUT.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "pulled_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "reference": "nadac_per_unit",
        "note": "Real public data. Median NADAC per unit across NDCs at the latest effective date. "
                "Facility invoice prices in line-items.json are authored (demo_grounded).",
        "drugs": out,
    }
    OUT.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"wrote {len(out)} drugs → {OUT.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
