"""
apps/onchain/db.py — Postgres (Neon) index over everything on-chain.

Design:
- Two tables: commits (every tx we make) + deliveries (proof-of-service w/ IPFS refs).
- Writes go here from /commit and /delivery BEFORE the API returns.
- Reads for /commits, /deliveries, /verify prefer the DB; JSONL stays as a
  disaster-recovery fallback if DB connectivity breaks.
- Chain remains the trust root (anyone can rehash + verify independently).
  This DB is just our index + the "delete everything" button for demo resets.

Enable: set DATABASE_URL in apps/onchain/.env. If unset, the service runs
in JSONL-only mode (prior behaviour).

Connection string shape (Neon default):
  postgresql://user:password@ep-xxxx.us-east-1.aws.neon.tech/dbname?sslmode=require
"""
from __future__ import annotations

import json
import os
import threading
from typing import Any, Optional

_lock = threading.Lock()
_conn = None
_pool = None


def _db_url() -> str:
    """Read DATABASE_URL lazily so .env loaded after this module's import still counts."""
    return os.getenv("DATABASE_URL", "").strip()


def enabled() -> bool:
    return bool(_db_url())


def _psycopg():
    """Lazy-import psycopg2. Keep the service runnable without it when DATABASE_URL isn't set."""
    import psycopg2
    import psycopg2.pool
    import psycopg2.extras
    return psycopg2


def init() -> None:
    """Create a thread-safe connection pool and ensure tables exist. Idempotent."""
    global _pool
    url = _db_url()
    if not url:
        return
    if _pool is not None:
        return
    with _lock:
        if _pool is not None:
            return
        psycopg2 = _psycopg()
        _pool = psycopg2.pool.ThreadedConnectionPool(1, 5, url)
        _ensure_schema()
        print("[db] connected to Postgres (pool 1..5)")


def _get_conn():
    if _pool is None:
        init()
    return _pool.getconn()


def _put_conn(conn) -> None:
    if _pool is not None and conn is not None:
        _pool.putconn(conn)


def _ensure_schema() -> None:
    sql = """
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
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
    finally:
        _put_conn(conn)


# ----- writes ---------------------------------------------------------------

def insert_commit(row: dict) -> None:
    if not enabled():
        return
    core = {k: row.get(k) for k in (
        "tx_hash", "claim_type", "claim_type_label", "claim_hash",
        "signer_role", "signer_address", "block_number", "explorer_url",
        "committed_at", "mocked", "error",
    )}
    # Keep anything else (image_cid etc. for claim_type=5) inside extra; dup fields in
    # the deliveries table.
    extra = {k: v for k, v in row.items() if k not in core}
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO commits
                   (tx_hash, claim_type, claim_type_label, claim_hash, signer_role, signer_address,
                    block_number, explorer_url, committed_at, mocked, error, extra)
                   VALUES (%(tx_hash)s, %(claim_type)s, %(claim_type_label)s, %(claim_hash)s,
                           %(signer_role)s, %(signer_address)s, %(block_number)s, %(explorer_url)s,
                           %(committed_at)s, %(mocked)s, %(error)s, %(extra)s::jsonb)
                   ON CONFLICT (tx_hash) DO NOTHING""",
                {**core, "mocked": bool(core.get("mocked")), "extra": json.dumps(extra or {})},
            )
        conn.commit()
    finally:
        _put_conn(conn)


def insert_delivery(row: dict) -> None:
    if not enabled():
        return
    fields = ("tx_hash", "facility_id", "patient_pseudonym", "staff_pseudonym",
              "service_type", "service_detail", "delivered_at", "image_cid", "image_url",
              "image_sha256", "image_mime", "metadata_cid", "metadata_url", "pin_mode")
    core = {f: row.get(f) for f in fields}
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""INSERT INTO deliveries ({', '.join(fields)})
                    VALUES ({', '.join('%(' + f + ')s' for f in fields)})
                    ON CONFLICT (tx_hash) DO NOTHING""",
                core,
            )
        conn.commit()
    finally:
        _put_conn(conn)


def update_block_number(tx_hash: str, block_number: int, signer_role: Optional[str] = None,
                        signer_address: Optional[str] = None) -> None:
    """Called when a backfill resolves the receipt. Idempotent."""
    if not enabled():
        return
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE commits SET block_number = COALESCE(block_number, %s),
                      signer_role = COALESCE(signer_role, %s),
                      signer_address = COALESCE(signer_address, %s)
                   WHERE tx_hash = %s""",
                (block_number, signer_role, signer_address, tx_hash),
            )
        conn.commit()
    finally:
        _put_conn(conn)


# ----- reads ----------------------------------------------------------------

def find_commits(claim_hash: Optional[str] = None, claim_type: Optional[int] = None,
                 limit: int = 100) -> list[dict]:
    if not enabled():
        return []
    where, args = [], []
    if claim_hash:
        where.append("claim_hash = %s"); args.append(claim_hash)
    if claim_type is not None:
        where.append("claim_type = %s"); args.append(claim_type)
    sql = "SELECT * FROM commits"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY committed_at DESC LIMIT %s"; args.append(limit)
    conn = _get_conn()
    try:
        from psycopg2.extras import RealDictCursor
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, args)
            rows = [dict(r) for r in cur.fetchall()]
        return [_serialize(r) for r in rows]
    finally:
        _put_conn(conn)


def get_commit(tx_hash: str) -> Optional[dict]:
    if not enabled():
        return None
    conn = _get_conn()
    try:
        from psycopg2.extras import RealDictCursor
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM commits WHERE tx_hash = %s", (tx_hash,))
            r = cur.fetchone()
        return _serialize(dict(r)) if r else None
    finally:
        _put_conn(conn)


def list_deliveries(facility_id: Optional[str] = None, limit: int = 50) -> list[dict]:
    if not enabled():
        return []
    conn = _get_conn()
    try:
        from psycopg2.extras import RealDictCursor
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if facility_id:
                cur.execute(
                    """SELECT c.*, d.* FROM deliveries d
                       JOIN commits c ON c.tx_hash = d.tx_hash
                       WHERE d.facility_id = %s
                       ORDER BY d.delivered_at DESC LIMIT %s""",
                    (facility_id, limit),
                )
            else:
                cur.execute(
                    """SELECT c.*, d.* FROM deliveries d
                       JOIN commits c ON c.tx_hash = d.tx_hash
                       ORDER BY d.delivered_at DESC LIMIT %s""",
                    (limit,),
                )
            rows = [dict(r) for r in cur.fetchall()]
        return [_serialize(r) for r in rows]
    finally:
        _put_conn(conn)


# ----- admin ----------------------------------------------------------------

def reset(scope: str = "all") -> dict:
    """scope: 'deliveries' | 'commits' | 'all'. Returns counts deleted."""
    if not enabled():
        return {"deliveries": 0, "commits": 0}
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            d = c = 0
            if scope in ("deliveries", "all"):
                cur.execute("DELETE FROM deliveries"); d = cur.rowcount
            if scope in ("commits", "all"):
                cur.execute("DELETE FROM commits"); c = cur.rowcount
        conn.commit()
        return {"deliveries": d, "commits": c}
    finally:
        _put_conn(conn)


# ----- helpers --------------------------------------------------------------

def _serialize(r: dict) -> dict:
    """Make the row JSON-serializable (datetimes → ISO strings)."""
    out = {}
    for k, v in r.items():
        if hasattr(v, "isoformat"):
            out[k] = v.isoformat()
        else:
            out[k] = v
    return out
