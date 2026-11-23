"""Turn SPEND scoring results into SignalCards (packages/schemas/signal-card.schema.json)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import scoring

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "data"
SPEND = DATA / "spend"

PBJ_URL = "https://data.cms.gov/quality-of-care/payroll-based-journal-daily-nurse-staffing"


def _load(name: str) -> dict:
    return json.loads((SPEND / name).read_text())


class Store:
    """All SPEND inputs, loaded once at startup."""

    def __init__(self) -> None:
        self.facilities = {f["id"]: f for f in json.loads((DATA / "facilities.json").read_text())}
        self.prices_doc = _load("prices.json")
        self.prices = self.prices_doc["drugs"]
        census_doc = _load("census.json")
        self.census = census_doc["facilities"]
        self.usage = census_doc["_meta"]["usage_assumptions"]
        self.line_items = _load("line-items.json")["facilities"]
        self.graphs = _load("ownership-graphs.json")["facilities"]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _pct(ratio: float) -> str:
    return f"+{round((ratio - 1) * 100)}%" if ratio >= 1 else f"{round((ratio - 1) * 100)}%"


def _graph_for_ui(graph: dict, facility_id: str, line_items: list[dict], related_path: list[str]) -> dict:
    """vis-network-ready graph: ownership edges + 'supplies' edges, related-party path flagged."""
    path_pairs = set(zip(related_path, related_path[1:])) | set(zip(related_path[1:], related_path))
    totals: dict[str, float] = {}
    for li in line_items:
        totals[li["supplier_id"]] = totals.get(li["supplier_id"], 0) + li["total"]
    edges = [{**e, "related_party": (e["from"], e["to"]) in path_pairs} for e in graph["edges"]]
    related_suppliers = {n for n in related_path if n != facility_id}
    for sid, total in totals.items():
        edges.append({"from": sid, "to": facility_id, "type": "supplies",
                      "label": f"invoiced ${total:,.0f} (Q3 2026)",
                      "related_party": sid in related_suppliers})
    return {"nodes": graph["nodes"], "edges": edges, "notes": graph["notes"]}


def spend_signals(store: Store, facility_id: str) -> list[dict]:
    fac = store.facilities[facility_id]
    items = store.line_items[facility_id]
    census = store.census[facility_id]
    graph = store.graphs[facility_id]
    now = _now()
    labels = {n["id"]: n["label"] for n in graph["nodes"]}

    price = scoring.ref_price_delta(items, store.prices)
    own = scoring.ownership_overlap(facility_id, [li["supplier_id"] for li in items], graph)
    vol = scoring.volume_sanity(items, census, store.usage)
    overall = scoring.spend_overall({"ref_price_delta": price["severity"],
                                     "ownership_overlap": own["severity"],
                                     "volume_sanity": vol["severity"]})

    related = {s["supplier_id"] for s in own["suppliers"] if s["severity"] == "red"}
    vol_by_line = {r["line_id"]: r for r in vol["rows"]}
    table = [{
        "line_id": r["line_id"], "invoice_no": r["invoice_no"], "invoice_date": r["invoice_date"],
        "drug": r["drug"], "ndc": r["ndc"], "unit": r["unit"], "qty": r["qty"],
        "unit_price": r["unit_price"], "total": r["total"],
        "supplier_id": r["supplier_id"], "supplier": labels.get(r["supplier_id"], r["supplier_id"]),
        "related_party_supplier": r["supplier_id"] in related,
        "reference_price": r["reference_price"], "price_ratio": r["price_ratio"],
        "price_severity": r["price_severity"],
        "expected_max_units": vol_by_line[r["line_id"]]["expected_max"],
        "volume_ratio": vol_by_line[r["line_id"]]["volume_ratio"],
        "volume_severity": vol_by_line[r["line_id"]]["volume_severity"],
    } for r in price["rows"]]

    pw = price["worst"]
    price_card = {
        "signal_id": f"spend-ref_price_delta-{facility_id}-{pw['line_id']}",
        "pillar": "spend", "signal_type": "ref_price_delta", "facility_id": facility_id,
        "severity": price["severity"],
        "headline": f"{pw['drug']} invoiced at {pw['price_ratio']}× NADAC ({_pct(pw['price_ratio'])})",
        "detail": (f"Supplier invoice {pw['invoice_no']} ({labels.get(pw['supplier_id'], pw['supplier_id'])}): "
                   f"${pw['unit_price']:,.2f}/{pw['unit']} vs CMS NADAC ${pw['reference_price']:,.2f}/{pw['unit']}. "
                   f"{sum(r['price_severity'] == 'red' for r in price['rows'])} of {len(price['rows'])} lines above 3×. "
                   "Invoices feed the facility cost report (CMS Form 2540)."),
        "data_provenance": "demo_grounded",
        "evidence": {"line_id": pw["line_id"], "drug": pw["drug"], "ndc": pw["ndc"],
                     "unit_price": pw["unit_price"], "reference_price": pw["reference_price"],
                     "ratio": pw["price_ratio"], "supplier_id": pw["supplier_id"],
                     "thresholds": {"red_above": scoring.PRICE_RED, "yellow_from": scoring.PRICE_YELLOW},
                     "reference": "CMS NADAC per unit, effective " + store.prices[pw["drug_id"]]["effective_date"],
                     "line_items": table},
        "citation": {"source": "CMS NADAC (National Average Drug Acquisition Cost) 2026",
                     "url": store.prices[pw["drug_id"]]["source_url"]},
        "computed_at": now,
    }

    ow = own["worst"]
    if ow["severity"] == "red":
        headline = (f"Supplier {labels[ow['supplier_id']]} shares owner {labels[ow['shared_node']]} "
                    f"with this facility ({ow['hops']} hops)")
    elif ow["severity"] == "yellow":
        headline = f"Supplier {labels[ow['supplier_id']]} shares a registered agent with this facility"
    else:
        headline = "No common ownership between facility and its suppliers"
    own_card = {
        "signal_id": f"spend-ownership_overlap-{facility_id}",
        "pillar": "spend", "signal_type": "ownership_overlap", "facility_id": facility_id,
        "severity": own["severity"], "headline": headline[:120],
        "detail": "Related-party path: " + " → ".join(labels.get(n, n) for n in ow["path"]) if ow["path"]
                  else "Suppliers checked: " + ", ".join(labels.get(s["supplier_id"], s["supplier_id"]) for s in own["suppliers"]),
        "data_provenance": "demo_grounded",
        "evidence": {"hops": ow["hops"], "shared_node": ow["shared_node"], "path": ow["path"],
                     "supplier_id": ow["supplier_id"], "suppliers": own["suppliers"],
                     "max_hops": scoring.MAX_HOPS,
                     "ownership_graph": _graph_for_ui(graph, facility_id, items, ow["path"])},
        "citation": fac["citation"],
        "computed_at": now,
    }

    vw = vol["worst"]
    vol_card = {
        "signal_id": f"spend-volume_sanity-{facility_id}-{vw['line_id']}",
        "pillar": "spend", "signal_type": "volume_sanity", "facility_id": facility_id,
        "severity": vol["severity"],
        "headline": (f"{vw['drug']}: {vw['billed_units']:,} billed vs ~{vw['expected_max']:,} expected "
                     f"({vw['volume_ratio']}×)")[:120],
        "detail": (f"{census['resident_days_quarter']:,} resident-days in {census['quarter']} "
                   f"(~{census['avg_residents']} residents). Assumes {round(vw['assumptions']['share_of_residents'] * 100)}% "
                   f"of residents on this drug at {vw['assumptions']['units_per_user_per_day']} {store.prices[vw['drug_id']]['invoice_unit']}/day."),
        "data_provenance": "demo_grounded",
        "evidence": {"drug": vw["drug"], "line_id": vw["line_id"], "billed_units": vw["billed_units"],
                     "expected_max": vw["expected_max"], "ratio": vw["volume_ratio"],
                     "resident_days": census["resident_days_quarter"], "census_source": census["source"],
                     "assumptions": vw["assumptions"],
                     "thresholds": {"red_above": scoring.VOLUME_RED, "yellow_from": scoring.VOLUME_YELLOW},
                     "rows": vol["rows"]},
        "citation": {"source": "CMS Payroll-Based Journal (resident-days; placeholder until PBJ pull)", "url": PBJ_URL},
        "computed_at": now,
    }

    sev = {"ref_price_delta": price["severity"], "ownership_overlap": own["severity"], "volume_sanity": vol["severity"]}
    n_red = sum(v == "red" for v in sev.values())
    n_yellow = sum(v == "yellow" for v in sev.values())
    flagged = ", ".join(f"{n} {c}" for n, c in ((n_red, "red"), (n_yellow, "yellow")) if n)
    overall_card = {
        "signal_id": f"spend-spend_overall-{facility_id}",
        "pillar": "spend", "signal_type": "spend_overall", "facility_id": facility_id,
        "severity": overall,
        "headline": {"red": "SPEND: all 3 signals red — refer to MFCU",
                     "yellow": f"SPEND: {flagged} of 3 signals — review, not referral",
                     "green": "SPEND: no procurement anomalies"}[overall],
        "detail": "Red only when price, ownership and volume all agree. Use this card for the facility roll-up.",
        "data_provenance": "demo_grounded",
        "evidence": sev,
        "computed_at": now,
    }
    return [price_card, own_card, vol_card, overall_card]
