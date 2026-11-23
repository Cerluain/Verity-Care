#!/usr/bin/env python3
"""
scripts/migrate.py — create / drop the Postgres index tables.

Usage from repo root:
  # Create tables (idempotent — safe to re-run)
  python scripts/migrate.py up

  # Drop everything (fast purge when the reset endpoint feels indirect)
  python scripts/migrate.py down

  # Drop then create — total reset
  python scripts/migrate.py reset

  # Just check connectivity and print row counts
  python scripts/migrate.py status

Reads DATABASE_URL from apps/onchain/.env. No deps outside psycopg2 + python-dotenv.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    import psycopg2
except ImportError:
    print("missing deps. run:  pip install psycopg2-binary python-dotenv")
    sys.exit(1)

REPO = Path(__file__).resolve().parent.parent
load_dotenv(REPO / "apps" / "onchain" / ".env")

DB_URL = os.getenv("DATABASE_URL", "").strip()
if not DB_URL:
    print("DATABASE_URL is empty in apps/onchain/.env — paste the Neon string first.")
    sys.exit(2)

SCHEMA_UP = """
CREATE TABLE IF NOT EXISTS commits (
    tx_hash           TEXT PRIMARY KEY,
    claim_type        INTEGER NOT NULL,
    claim_type_label  TEXT NOT NULL,
    claim_hash        TEXT NOT NULL,
    signer_role       TEXT,
    signer_address    TEXT,
    block_number      BIGINT,
    explorer_url      TEXT,
    committed_at      TIMESTAMPTZ NOT NULL,
    mocked            BOOLEAN NOT NULL DEFAULT FALSE,
    error             TEXT,
    extra             JSONB
);
CREATE INDEX IF NOT EXISTS commits_claim_hash_idx ON commits (claim_hash);
CREATE INDEX IF NOT EXISTS commits_claim_type_idx ON commits (claim_type);

CREATE TABLE IF NOT EXISTS deliveries (
    tx_hash           TEXT PRIMARY KEY REFERENCES commits (tx_hash) ON DELETE CASCADE,
    facility_id       TEXT NOT NULL,
    patient_pseudonym TEXT NOT NULL,
    staff_pseudonym   TEXT NOT NULL,
    service_type      TEXT NOT NULL,
    service_detail    TEXT,
    delivered_at      TIMESTAMPTZ NOT NULL,
    image_cid         TEXT,
    image_url         TEXT,
    image_sha256      TEXT,
    image_mime        TEXT,
    metadata_cid      TEXT,
    metadata_url      TEXT,
    pin_mode          TEXT
);
CREATE INDEX IF NOT EXISTS deliveries_facility_idx ON deliveries (facility_id);
CREATE INDEX IF NOT EXISTS deliveries_patient_idx  ON deliveries (patient_pseudonym);
"""

SCHEMA_DOWN = "DROP TABLE IF EXISTS deliveries; DROP TABLE IF EXISTS commits;"


def run(sql: str) -> None:
    conn = psycopg2.connect(DB_URL)
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
    finally:
        conn.close()


def status() -> None:
    conn = psycopg2.connect(DB_URL)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name IN ('commits','deliveries')
                ORDER BY table_name
            """)
            tables = [r[0] for r in cur.fetchall()]
            print(f"tables present: {tables}")
            for t in tables:
                cur.execute(f"SELECT COUNT(*) FROM {t}")
                print(f"  {t:14s} rows = {cur.fetchone()[0]}")
    finally:
        conn.close()


def main():
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "status").lower()
    host = DB_URL.split("@", 1)[-1].split("/", 1)[0] if "@" in DB_URL else "?"
    print(f"→ {host}  ({cmd})")
    if cmd == "up":
        run(SCHEMA_UP); print("✓ tables ready")
    elif cmd == "down":
        run(SCHEMA_DOWN); print("✓ tables dropped")
    elif cmd == "reset":
        run(SCHEMA_DOWN); run(SCHEMA_UP); print("✓ reset (drop + recreate)")
    elif cmd == "status":
        status()
    else:
        print(f"unknown command: {cmd}. use: up | down | reset | status")
        sys.exit(2)


if __name__ == "__main__":
    main()
