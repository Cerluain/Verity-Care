"""SPEND scoring: three signals + a pillar-level roll-up. Pure functions, no web code.

Thresholds (apps/phantom-spend/README.md + contexts/abi.md):
  ref_price_delta    red > 3x reference, yellow 1.5–3x, green < 1.5x   (worst line decides)
  ownership_overlap  red = supplier shares an owner with the facility within MAX_HOPS
                     yellow = shared registered agent only, green = no overlap
  volume_sanity      red > 1.5x expected max, yellow 1.2–1.5x, green <= 1.2x (worst line decides)
  spend_overall      red only if all three red; yellow if any red/yellow; else green
"""

from __future__ import annotations

from collections import deque

PRICE_RED, PRICE_YELLOW = 3.0, 1.5
VOLUME_RED, VOLUME_YELLOW = 1.5, 1.2
MAX_HOPS = 3

RANK = {"green": 0, "yellow": 1, "red": 2}


def band(ratio: float, red: float, yellow: float) -> str:
    if ratio > red:
        return "red"
    if ratio >= yellow:
        return "yellow"
    return "green"


# ----------------------------------------------------------------------------- price
def ref_price_delta(line_items: list[dict], prices: dict) -> dict:
    rows = []
    for li in line_items:
        ref = prices[li["drug_id"]]["reference_price_per_invoice_unit"]
        ratio = li["unit_price"] / ref
        rows.append({**li, "reference_price": ref, "price_ratio": round(ratio, 2),
                     "price_severity": band(ratio, PRICE_RED, PRICE_YELLOW)})
    worst = max(rows, key=lambda r: r["price_ratio"])
    return {"severity": worst["price_severity"], "worst": worst, "rows": rows}


# ----------------------------------------------------------------------------- ownership
def _ancestors(start: str, parents: dict[str, list[str]]) -> dict[str, int]:
    """node -> hop distance, walking owned_by edges upward (start itself at 0)."""
    dist = {start: 0}
    q = deque([start])
    while q:
        n = q.popleft()
        for p in parents.get(n, []):
            if p not in dist:
                dist[p] = dist[n] + 1
                q.append(p)
    return dist


def _path_up(start: str, target: str, parents: dict[str, list[str]]) -> list[str]:
    prev = {start: None}
    q = deque([start])
    while q:
        n = q.popleft()
        if n == target:
            break
        for p in parents.get(n, []):
            if p not in prev:
                prev[p] = n
                q.append(p)
    path, n = [], target
    while n is not None:
        path.append(n)
        n = prev[n]
    return list(reversed(path))


def ownership_overlap(facility_id: str, supplier_ids: list[str], graph: dict) -> dict:
    parents: dict[str, list[str]] = {}
    agents: dict[str, set[str]] = {}
    for e in graph["edges"]:
        if e["type"] == "owned_by":
            parents.setdefault(e["from"], []).append(e["to"])
        elif e["type"] == "registered_agent":
            agents.setdefault(e["from"], set()).add(e["to"])

    fac_anc = _ancestors(facility_id, parents)
    fac_agents = set().union(*(agents.get(n, set()) for n in fac_anc))

    results = []
    for sid in sorted(set(supplier_ids)):
        sup_anc = _ancestors(sid, parents)
        shared = [(fac_anc[n] + sup_anc[n], n) for n in fac_anc.keys() & sup_anc.keys()]
        shared_agents = sorted(fac_agents & set().union(*(agents.get(n, set()) for n in sup_anc)))
        if shared:
            hops, anc = min(shared)
            path = _path_up(facility_id, anc, parents) + list(reversed(_path_up(sid, anc, parents)))[1:]
            sev = "red" if hops <= MAX_HOPS else "yellow"
            results.append({"supplier_id": sid, "severity": sev, "hops": hops, "shared_node": anc,
                            "path": path, "shared_registered_agents": shared_agents})
        elif shared_agents:
            results.append({"supplier_id": sid, "severity": "yellow", "hops": None, "shared_node": None,
                            "path": [], "shared_registered_agents": shared_agents})
        else:
            results.append({"supplier_id": sid, "severity": "green", "hops": None, "shared_node": None,
                            "path": [], "shared_registered_agents": []})

    worst = max(results, key=lambda r: (RANK[r["severity"]], -(r["hops"] or 99)))
    return {"severity": worst["severity"], "worst": worst, "suppliers": results}


# ----------------------------------------------------------------------------- volume
def volume_sanity(line_items: list[dict], census: dict, usage: dict) -> dict:
    rdays = census["resident_days_quarter"]
    rows = []
    for li in line_items:
        u = usage[li["drug_id"]]
        expected = rdays * u["share_of_residents"] * u["units_per_user_per_day"]
        ratio = li["qty"] / expected
        rows.append({"line_id": li["line_id"], "drug_id": li["drug_id"], "drug": li["drug"],
                     "billed_units": li["qty"], "expected_max": round(expected),
                     "volume_ratio": round(ratio, 2),
                     "volume_severity": band(ratio, VOLUME_RED, VOLUME_YELLOW),
                     "assumptions": u})
    worst = max(rows, key=lambda r: r["volume_ratio"])
    return {"severity": worst["volume_severity"], "worst": worst, "rows": rows}


# ----------------------------------------------------------------------------- roll-up
def spend_overall(severities: dict[str, str]) -> str:
    vals = list(severities.values())
    if all(v == "red" for v in vals):
        return "red"
    if any(v in ("red", "yellow") for v in vals):
        return "yellow"
    return "green"
