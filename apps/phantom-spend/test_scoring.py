"""Run: .venv/bin/pytest -q   (from apps/phantom-spend)"""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator

import scoring
from main import app

REPO = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((REPO / "packages/schemas/signal-card.schema.json").read_text())
validator = Draft202012Validator(SCHEMA)
client = TestClient(app)

EXPECTED = {
    #  facility id                         price     ownership  volume    overall
    "buffalo-center-centers-health":     ("red",    "red",     "red",    "red"),
    "accordius-rose-manor-portopiccolo": ("red",    "red",     "red",    "red"),
    "mi-casa-life-care-az":              ("yellow", "green",   "green",  "yellow"),
    "crook-county-wy-rural":             ("red",    "green",   "green",  "yellow"),  # rural check
    "terraces-phoenix-humangood":        ("green",  "green",   "green",  "green"),
    "haven-health-green-valley":         ("green",  "green",   "green",  "green"),
}
TYPES = ["ref_price_delta", "ownership_overlap", "volume_sanity", "spend_overall"]


def signals(fid):
    r = client.get(f"/spend/{fid}")
    assert r.status_code == 200
    return {c["signal_type"]: c for c in r.json()["signals"]}


@pytest.mark.parametrize("fid,expected", EXPECTED.items())
def test_expected_colours(fid, expected):
    s = signals(fid)
    assert [s[t]["severity"] for t in TYPES] == list(expected)


@pytest.mark.parametrize("fid", EXPECTED)
def test_cards_match_shared_schema(fid):
    r = client.get(f"/spend/{fid}").json()
    assert len(r["signals"]) == 4
    for card in r["signals"]:
        errors = [e.message for e in validator.iter_errors(card)]
        assert not errors, (card["signal_id"], errors)
        assert len(card["headline"]) < 120
        assert card["data_provenance"] == "demo_grounded"


def test_ownership_graph_is_drawable():
    g = signals("buffalo-center-centers-health")["ownership_overlap"]["evidence"]["ownership_graph"]
    ids = {n["id"] for n in g["nodes"]}
    assert all(e["from"] in ids and e["to"] in ids for e in g["edges"])
    assert any(e["related_party"] for e in g["edges"])


def test_table_has_12_rows():
    rows = signals("buffalo-center-centers-health")["ref_price_delta"]["evidence"]["line_items"]
    assert len(rows) == 12


def test_all_facilities_covered():
    ids = {f["id"] for f in json.loads((REPO / "data/facilities.json").read_text())}
    assert ids == set(EXPECTED)
    assert {f["id"] for f in client.get("/spend").json()["facilities"]} == ids


def test_unknown_facility_404():
    assert client.get("/spend/nope").status_code == 404


def test_spend_overall_rule():
    assert scoring.spend_overall({"a": "red", "b": "red", "c": "red"}) == "red"
    assert scoring.spend_overall({"a": "red", "b": "green", "c": "green"}) == "yellow"
    assert scoring.spend_overall({"a": "green", "b": "green", "c": "green"}) == "green"
