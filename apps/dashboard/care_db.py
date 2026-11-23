"""SQLite store for the guardian timeline + staff check-ins (Dev A).

One file: data/care/runtime/care.db (gitignored). Created and seeded on first use;
`reset()` wipes and re-seeds (POST /care/reset before each demo run).

Everything here is SYNTHETIC: residents, guardians, staff. No real people, no PHI.
Go-live = today: days before today have "no records before Verity Care go-live".
"""
from __future__ import annotations

import json
import sqlite3
import threading
from datetime import date, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = REPO_ROOT / "data" / "care" / "runtime" / "care.db"
FACILITY_ID = "mi-casa-life-care-az"
FACILITY_NAME = "Mi Casa Nursing Center"

_lock = threading.Lock()

SCHEMA = """
CREATE TABLE residents (
  id TEXT PRIMARY KEY, name TEXT, age INT, room TEXT, facility_id TEXT, facility_name TEXT,
  admitted TEXT, profile_json TEXT);
CREATE TABLE guardians (
  id TEXT PRIMARY KEY, resident_id TEXT, name TEXT, relation TEXT, phone TEXT);
CREATE TABLE staff (
  id TEXT PRIMARY KEY, name TEXT, role TEXT, shift TEXT, facility_id TEXT);
CREATE TABLE assignments (staff_id TEXT, resident_id TEXT, PRIMARY KEY (staff_id, resident_id));
CREATE TABLE care_plan (
  id TEXT PRIMARY KEY, resident_id TEXT, time TEXT, category TEXT, title TEXT, detail TEXT,
  role TEXT, billed TEXT, owner TEXT);
CREATE TABLE check_ins (
  id TEXT PRIMARY KEY, plan_item_id TEXT, resident_id TEXT, staff_id TEXT, day TEXT,
  captured_at TEXT, note TEXT, seeded INT DEFAULT 0, photo_url TEXT, photo_sha256 TEXT,
  claim_hash TEXT, tx_hash TEXT, explorer_url TEXT, signer_role TEXT, mocked INT,
  image_cid TEXT, metadata_cid TEXT, image_url TEXT, metadata_url TEXT, pin_mode TEXT);
CREATE TABLE disputes (
  id TEXT PRIMARY KEY, plan_item_id TEXT, resident_id TEXT, day TEXT, reason TEXT,
  created_at TEXT, route_json TEXT, status TEXT);
CREATE TABLE history (
  resident_id TEXT, day TEXT, kind TEXT, title TEXT, detail TEXT);
"""

# --------------------------------------------------------------------------- seed data
STAFF = [
    ("RN-1187",  "Priya S.",  "RN",  "Day 7a–7p"),
    ("LPN-0412", "Marcus L.", "LPN", "Day 7a–7p"),
    ("PT-0907",  "Kevin O.",  "PT",  "Day 8a–4p"),   # therapy owner; not a demo login
]

RESIDENTS = [
    {"id": "res-rosa", "name": "Rosa D.", "age": 82, "room": "214B", "admitted": "2025-03-14",
     "guardian": ("Daniel D.", "son"),
     "conditions": ["Type 2 diabetes (insulin)", "Early-stage dementia", "Hip replacement rehab"],
     "allergies": ["Penicillin"],
     "meds": [("Insulin lispro", "6 units", "with meals"), ("Donepezil", "10 mg", "08:00"),
              ("Lisinopril", "10 mg", "08:00"), ("Atorvastatin", "40 mg", "20:00")],
     "therapy": ["pt", "ot"], "insulin": True, "diet": "Diabetic, soft",
     "physician": "Dr. A. Ruiz (synthetic)", "billing": {"pt_billed": 22, "pt_verified": 9, "ot_billed": 18, "ot_verified": 14},
     "history": [("2025-03-14", "admission", "Admitted after hip replacement", "Transferred from Banner (synthetic)"),
                 ("2025-06-02", "care_plan", "Care-plan meeting", "Daniel attended by phone; insulin increased to 6 units"),
                 ("2025-11-19", "incident", "Fall in bathroom, no injury", "Reported to family the next day"),
                 ("2026-08-30", "hospital", "ER visit: low blood sugar", "Returned same day"),
                 ("2026-10-12", "care_plan", "Quarterly review", "PT continued 5×/week")]},
    {"id": "res-walter", "name": "Walter K.", "age": 88, "room": "108A", "admitted": "2024-09-02",
     "guardian": ("Linda K.", "daughter"),
     "conditions": ["Congestive heart failure", "Hypertension"], "allergies": ["Sulfa drugs"],
     "meds": [("Furosemide", "40 mg", "08:00"), ("Lisinopril", "10 mg", "08:00"), ("Eliquis", "5 mg", "08:00 / 20:00")],
     "therapy": [], "insulin": False, "diet": "Low sodium", "physician": "Dr. M. Chen (synthetic)",
     "billing": {}, "history": [("2024-09-02", "admission", "Admitted for long-term care", ""),
                                ("2026-04-17", "hospital", "Hospital stay: fluid overload", "4 days")]},
    {"id": "res-mae", "name": "Mae T.", "age": 79, "room": "210A", "admitted": "2026-09-21",
     "guardian": ("James T.", "husband"),
     "conditions": ["Stroke recovery (left side)", "Dysphagia"], "allergies": [],
     "meds": [("Eliquis", "5 mg", "08:00 / 20:00"), ("Atorvastatin", "40 mg", "20:00")],
     "therapy": ["pt", "ot"], "insulin": False, "diet": "Pureed, thickened liquids",
     "physician": "Dr. A. Ruiz (synthetic)", "billing": {"pt_billed": 20, "pt_verified": 19, "ot_billed": 15, "ot_verified": 15},
     "history": [("2026-09-21", "admission", "Admitted for stroke rehab", "Short-stay Medicare Part A")]},

]

# Who does each task. Rosa = Priya, Mae = Marcus, Walter is shared
# (Priya: medications; Marcus: vitals, meals, activity). Therapy = the physical therapist.
NURSE = {"res-rosa": "RN-1187", "res-mae": "LPN-0412"}


def _owner(rid: str, category: str) -> str:
    if category == "therapy":
        return "PT-0907"
    if rid == "res-walter":
        return "RN-1187" if category == "medication" else "LPN-0412"
    return NURSE[rid]


ASSIGN = {  # staff -> residents (derived from task owners)
    "RN-1187": ["res-rosa", "res-walter"],
    "LPN-0412": ["res-walter", "res-mae"],
    "PT-0907": ["res-rosa", "res-mae"],
}


def _plan(r: dict) -> list[tuple]:
    """(id, time, category, title, detail, role, billed)"""
    p = [("vitals-am", "07:30", "vitals", "Morning vitals", "Blood pressure, pulse" + (", blood sugar" if r["insulin"] else ""), "LPN", None)]
    if r["insulin"]:
        p.append(("insulin-am", "07:45", "medication", "Insulin lispro", r["meds"][0][1] + " before breakfast", "RN", None))
    am = [m for m in r["meds"] if "08:00" in m[2]]
    if am:
        p.append(("meds-am", "08:00", "medication", "Morning medications", ", ".join(f"{m[0]} {m[1]}" for m in am), "RN", None))
    p.append(("breakfast", "09:00", "meal", "Breakfast", r["diet"] + " menu", "CNA", None))
    if "pt" in r["therapy"]:
        p.append(("pt-am", "10:30", "therapy", "Physical therapy, 30 min", "Strength and walking", "PT", "Medicare Part B · 2 units"))
    p.append(("lunch", "12:00", "meal", "Lunch", r["diet"] + " menu", "CNA", None))
    if r["insulin"]:
        p.append(("insulin-noon", "12:15", "medication", "Insulin lispro", r["meds"][0][1] + " with lunch", "RN", None))
    p.append(("activity", "14:00", "activity", "Music group", "Day room", "CNA", None))
    if "ot" in r["therapy"]:
        p.append(("ot-pm", "15:00", "therapy", "Occupational therapy, 30 min", "Daily-living skills", "OT", "Medicare Part B · 2 units"))
    p.append(("dinner", "17:30", "meal", "Dinner", r["diet"] + " menu", "CNA", None))
    pm = [m for m in r["meds"] if "20:00" in m[2]]
    if pm:
        p.append(("meds-pm", "20:00", "medication", "Evening medications", ", ".join(f"{m[0]} {m[1]}" for m in pm), "RN", None))
    return p


# By default nothing is pre-checked. Every item on the plan must be photo-verified
# by staff before it moves from 'upcoming/not_verified' → 'verified' on the guardian
# timeline. Keeps the demo honest: if you want green ticks, you have to take photos.
SEED_DONE: dict = {}


def _seed(db: sqlite3.Connection) -> None:
    db.executescript(SCHEMA)
    today = date.today().isoformat()
    for sid, name, role, shift in STAFF:
        db.execute("INSERT INTO staff VALUES (?,?,?,?,?)", (sid, name, role, shift, FACILITY_ID))
    for sid, rids in ASSIGN.items():
        for rid in rids:
            db.execute("INSERT INTO assignments VALUES (?,?)", (sid, rid))
    for r in RESIDENTS:
        profile = {k: r[k] for k in ("conditions", "allergies", "diet", "physician", "billing")}
        profile["meds"] = [{"name": m[0], "dose": m[1], "when": m[2]} for m in r["meds"]]
        profile["care_team"] = [{"id": s, "name": n, "role": ro} for s, n, ro, _ in STAFF if r["id"] in ASSIGN[s]]
        db.execute("INSERT INTO residents VALUES (?,?,?,?,?,?,?,?)",
                   (r["id"], r["name"], r["age"], r["room"], FACILITY_ID, FACILITY_NAME, r["admitted"], json.dumps(profile)))
        g = r["guardian"]
        db.execute("INSERT INTO guardians VALUES (?,?,?,?,?)", ("g-" + r["id"][4:], r["id"], g[0], g[1], "(555) 010-0000"))
        for pid, t, cat, title, detail, role, billed in _plan(r):
            db.execute("INSERT INTO care_plan VALUES (?,?,?,?,?,?,?,?,?)",
                       (f"{r['id']}:{pid}", r["id"], t, cat, title, detail, role, billed, _owner(r["id"], cat)))
        for d, kind, title, detail in r["history"]:
            db.execute("INSERT INTO history VALUES (?,?,?,?,?)", (r["id"], d, kind, title, detail))
        for i, (pid, sid, t, note) in enumerate(SEED_DONE.get(r["id"], [])):
            db.execute("""INSERT INTO check_ins (id, plan_item_id, resident_id, staff_id, day, captured_at, note,
                          seeded, tx_hash, signer_role, mocked) VALUES (?,?,?,?,?,?,?,1,?,?,1)""",
                       (f"seed-{r['id']}-{i}", f"{r['id']}:{pid}", r["id"], sid, today, t, note,
                        "0xseed" + f"{abs(hash((r['id'], pid))) :x}"[:12], "staff"))
    db.commit()


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    fresh = not DB_PATH.exists()
    db = sqlite3.connect(DB_PATH, check_same_thread=False)
    db.row_factory = sqlite3.Row
    if fresh:
        _seed(db)
    else:
        # A DB seeded on an earlier day: move seeded morning history to today.
        db.execute("UPDATE check_ins SET day=? WHERE seeded=1", (date.today().isoformat(),))
        db.commit()
    return db


def reset() -> None:
    with _lock:
        if DB_PATH.exists():
            DB_PATH.unlink()
        connect().close()


GO_LIVE = date.today  # callable: go-live is "today" for the demo


def days_back(n: int = 7) -> list[str]:
    t = date.today()
    return [(t - timedelta(days=i)).isoformat() for i in range(n)]
