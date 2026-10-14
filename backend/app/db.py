from __future__ import annotations

import base64
import hashlib
import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone

from .config import DB_PATH
from .models import AppSettings, AuditEntry, Invoice

# Records store for ConciliaBot. Everything the agent does is recorded in a
# per-connection, append-only, hash-chained journal so that a third party can
# verify the bot never altered anything. Source documents are referenced by
# hash and, optionally, stored encrypted with a retention deadline.
#
# Two levels of data are kept deliberately separate:
#   * operational records (transactions, audit, approvals) -> always persisted
#   * the fiscal source document -> referenced by hash; only the ciphertext
#     when an encryption key is configured, and purged after retention.

GENESIS_HASH = "0" * 64

SCHEMA = """
CREATE TABLE IF NOT EXISTS connections (
    id TEXT PRIMARY KEY,
    erp_kind TEXT NOT NULL,
    base_url TEXT,
    tenant_ref TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS transactions (
    id TEXT PRIMARY KEY,
    connection_id TEXT NOT NULL,
    doc_type TEXT NOT NULL DEFAULT 'invoice',
    external_ref TEXT,
    folio TEXT,
    uuid TEXT,
    currency TEXT,
    total REAL,
    status TEXT NOT NULL,
    po_ref TEXT,
    delivery_note_ref TEXT,
    created_at TEXT,
    payload TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tx_conn ON transactions(connection_id);
CREATE INDEX IF NOT EXISTS idx_tx_conn_uuid ON transactions(connection_id, uuid);
CREATE TABLE IF NOT EXISTS audit (
    id TEXT PRIMARY KEY,
    connection_id TEXT NOT NULL,
    transaction_id TEXT NOT NULL,
    at TEXT NOT NULL,
    actor_kind TEXT NOT NULL,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    detail TEXT NOT NULL,
    prev_hash TEXT NOT NULL,
    hash TEXT NOT NULL,
    payload TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_audit_conn ON audit(connection_id);
CREATE INDEX IF NOT EXISTS idx_audit_tx ON audit(transaction_id);
CREATE TABLE IF NOT EXISTS approvals (
    id TEXT PRIMARY KEY,
    connection_id TEXT NOT NULL,
    transaction_id TEXT NOT NULL,
    at TEXT NOT NULL,
    actor TEXT NOT NULL,
    decision TEXT NOT NULL,
    note TEXT,
    payload TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_approvals_tx ON approvals(transaction_id);
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    connection_id TEXT NOT NULL,
    transaction_id TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    cipher TEXT,
    nonce TEXT,
    created_at TEXT NOT NULL,
    retention_until TEXT
);
CREATE INDEX IF NOT EXISTS idx_docs_conn ON documents(connection_id);
CREATE INDEX IF NOT EXISTS idx_docs_tx ON documents(transaction_id);
CREATE TABLE IF NOT EXISTS kv (
    key TEXT PRIMARY KEY,
    payload TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def default_connection_id() -> str:
    try:
        from . import erp_config

        return erp_config.active_connection_id()
    except Exception:  # noqa: BLE001 - never let config resolution break storage
        return "demo"


def ensure_connection(connection_id: str | None = None) -> str:
    """Register the active connection row (idempotent) and return its id."""
    try:
        from . import erp_config

        meta = erp_config.connection_meta()
    except Exception:  # noqa: BLE001
        meta = {"id": "demo", "erp_kind": "demo", "base_url": "sandbox", "tenant_ref": ""}
    cid = connection_id or meta["id"]
    conn = get_conn()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO connections (id, erp_kind, base_url, tenant_ref, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (cid, meta.get("erp_kind", ""), meta.get("base_url", ""), meta.get("tenant_ref", ""), _now()),
        )
        conn.commit()
    finally:
        conn.close()
    return cid


def _table_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    try:
        return [r["name"] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    except sqlite3.DatabaseError:
        return []


def _read_legacy_invoices(conn: sqlite3.Connection) -> list[str] | None:
    """Old single-tenant `invoices` table (no connection_id). Returns payloads."""
    cols = _table_columns(conn, "invoices")
    if not cols or "connection_id" in cols:
        return None
    return [r["payload"] for r in conn.execute("SELECT payload FROM invoices").fetchall()]


def _read_legacy_audit(conn: sqlite3.Connection) -> list[str] | None:
    """Old `audit` table (no hash chain). Returns payloads in insert order."""
    cols = _table_columns(conn, "audit")
    if not cols or "hash" in cols:
        return None
    return [r["payload"] for r in conn.execute("SELECT payload FROM audit ORDER BY rowid").fetchall()]


def _safe_json(payload: str) -> dict:
    try:
        data = json.loads(payload)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}


def init_db() -> None:
    conn = get_conn()
    try:
        legacy_invoices = _read_legacy_invoices(conn)
        legacy_audit = _read_legacy_audit(conn)
        if legacy_audit is not None:
            conn.execute("DROP TABLE audit")
        if legacy_invoices is not None:
            conn.execute("DROP TABLE invoices")
        conn.executescript(SCHEMA)

        if legacy_invoices:
            conn.execute(
                "INSERT OR IGNORE INTO connections (id, erp_kind, base_url, tenant_ref, created_at)"
                " VALUES ('demo', 'demo', 'sandbox', '', ?)",
                (_now(),),
            )
            for payload in legacy_invoices:
                _insert_transaction_from_payload(conn, "demo", payload)
        for payload in legacy_audit or []:
            from .models import AuditEntry as _AuditEntry

                # noqa: E501 - build from the legacy camelCase payload
            _append_audit_row(conn, "demo", AuditEntry.model_validate_json(payload))
        conn.commit()
    finally:
        conn.close()


def _count(table: str) -> int:
    conn = get_conn()
    try:
        row = conn.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()
        return int(row["n"])
    finally:
        conn.close()


def is_empty() -> bool:
    return _count("transactions") == 0


# --- transactions ---------------------------------------------------------


def _insert_transaction_from_payload(conn: sqlite3.Connection, cid: str, payload: str) -> None:
    data = _safe_json(payload)
    po = data.get("purchaseOrder") or {}
    dn = data.get("deliveryNote") or {}
    conn.execute(
        """
        INSERT OR IGNORE INTO transactions
            (id, connection_id, doc_type, external_ref, folio, uuid, currency,
             total, status, po_ref, delivery_note_ref, created_at, payload)
        VALUES (?, ?, 'invoice', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data.get("id", ""),
            cid,
            data.get("folio", ""),
            data.get("folio", ""),
            data.get("uuid", ""),
            data.get("currency", ""),
            data.get("total"),
            data.get("status", "ingested"),
            po.get("number"),
            dn.get("number"),
            data.get("createdAt", ""),
            payload,
        ),
    )


def store_invoice(inv: Invoice, connection_id: str | None = None) -> Invoice:
    cid = ensure_connection(connection_id or default_connection_id())
    po_ref = inv.purchase_order.number if inv.purchase_order else None
    dn_ref = inv.delivery_note.number if inv.delivery_note else None
    conn = get_conn()
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO transactions
                (id, connection_id, doc_type, external_ref, folio, uuid, currency,
                 total, status, po_ref, delivery_note_ref, created_at, payload)
            VALUES (?, ?, 'invoice', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                inv.id,
                cid,
                inv.folio,
                inv.folio,
                inv.uuid,
                inv.currency,
                inv.total,
                inv.status.value,
                po_ref,
                dn_ref,
                inv.created_at,
                inv.model_dump_json(by_alias=True),
            ),
        )
        conn.commit()
        return inv
    finally:
        conn.close()


def list_invoices(connection_id: str | None = None) -> list[Invoice]:
    cid = connection_id or default_connection_id()
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT payload FROM transactions"
            " WHERE connection_id = ? AND doc_type = 'invoice'"
            " ORDER BY created_at DESC",
            (cid,),
        ).fetchall()
        return [Invoice.model_validate_json(r["payload"]) for r in rows]
    finally:
        conn.close()


def get_invoice(invoice_id: str, connection_id: str | None = None) -> Invoice | None:
    cid = connection_id or default_connection_id()
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT payload FROM transactions WHERE id = ? AND connection_id = ?",
            (invoice_id, cid),
        ).fetchone()
        return Invoice.model_validate_json(row["payload"]) if row else None
    finally:
        conn.close()


def get_invoice_by_uuid(uuid: str, connection_id: str | None = None) -> Invoice | None:
    cid = connection_id or default_connection_id()
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT payload FROM transactions"
            " WHERE connection_id = ? AND uuid = ? AND doc_type = 'invoice'"
            " ORDER BY created_at LIMIT 1",
            (cid, uuid),
        ).fetchone()
        return Invoice.model_validate_json(row["payload"]) if row else None
    finally:
        conn.close()


def next_invoice_id() -> str:
    conn = get_conn()
    try:
        row = conn.execute("SELECT payload FROM kv WHERE key = 'invoice_seq'").fetchone()
        seq = int(json.loads(row["payload"])) if row else 1000
        seq += 1
        conn.execute(
            "INSERT OR REPLACE INTO kv (key, payload) VALUES ('invoice_seq', ?)",
            (json.dumps(seq),),
        )
        conn.commit()
        return f"F-{seq}"
    finally:
        conn.close()


# --- audit (append-only, hash-chained) ------------------------------------


def _actor_kind(actor: str) -> str:
    value = (actor or "").strip().lower()
    if value == "agente":
        return "agente"
    if value == "sistema":
        return "sistema"
    return "humano"


def _audit_digest(
    prev_hash: str,
    connection_id: str,
    transaction_id: str,
    at: str,
    actor_kind: str,
    actor: str,
    action: str,
    detail: str,
) -> str:
    material = "\x1f".join(
        [prev_hash, connection_id, transaction_id, at, actor_kind, actor, action, detail]
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _next_audit_id(conn: sqlite3.Connection) -> str:
    row = conn.execute("SELECT COUNT(*) AS n FROM audit").fetchone()
    return f"A-{int(row['n']) + 1:04d}"


def _last_hash(conn: sqlite3.Connection, connection_id: str) -> str:
    row = conn.execute(
        "SELECT hash FROM audit WHERE connection_id = ? ORDER BY rowid DESC LIMIT 1",
        (connection_id,),
    ).fetchone()
    return row["hash"] if row else "0" * 64


def _append_audit_row(conn: sqlite3.Connection, connection_id: str, entry: AuditEntry) -> AuditEntry:
    audit_id = entry.id or _next_audit_id(conn)
    kind = entry.actor_kind or _actor_kind(entry.actor)
    prev_hash = _last_hash(conn, connection_id)
    digest = _audit_digest(
        prev_hash, connection_id, entry.invoice_id, entry.at, kind, entry.actor, entry.action, entry.detail
    )
    stored = entry.model_copy(
        update={
            "id": audit_id,
            "connection_id": connection_id,
            "actor_kind": kind,
            "prev_hash": prev_hash,
            "hash": digest,
        }
    )
    conn.execute(
        """
        INSERT INTO audit
            (id, connection_id, transaction_id, at, actor_kind, actor, action,
             detail, prev_hash, hash, payload)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            audit_id,
            connection_id,
            entry.invoice_id,
            entry.at,
            kind,
            entry.actor,
            entry.action,
            entry.detail,
            prev_hash,
            digest,
            stored.model_dump_json(by_alias=True),
        ),
    )
    conn.commit()
    return stored


def append_audit(entry: AuditEntry, connection_id: str | None = None) -> AuditEntry:
    cid = connection_id or default_connection_id()
    conn = get_conn()
    try:
        return _append_audit_row(conn, cid, entry)
    finally:
        conn.close()


def list_audit(connection_id: str | None = None, limit: int | None = None) -> list[AuditEntry]:
    cid = connection_id or default_connection_id()
    conn = get_conn()
    try:
        sql = "SELECT payload FROM audit WHERE connection_id = ? ORDER BY rowid DESC"
        params: tuple = (cid,)
        if limit:
            sql += " LIMIT ?"
            params = (cid, int(limit))
        rows = conn.execute(sql, params).fetchall()
        return [AuditEntry.model_validate_json(r["payload"]) for r in rows]
    finally:
        conn.close()


def verify_audit_chain(connection_id: str | None = None) -> dict:
    """Recompute the hash chain; returns ok/broken_at so tampering is provable."""
    cid = connection_id or default_connection_id()
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM audit WHERE connection_id = ? ORDER BY rowid ASC", (cid,)
        ).fetchall()
        prev = "0" * 64
        for row in rows:
            digest = _audit_digest(
                prev,
                row["connection_id"],
                row["transaction_id"],
                row["at"],
                row["actor_kind"],
                row["actor"],
                row["action"],
                row["detail"],
            )
            if row["prev_hash"] != prev or row["hash"] != digest:
                return {"ok": False, "brokenAt": row["id"], "count": len(rows)}
            prev = row["hash"]
        return {"ok": True, "brokenAt": None, "count": len(rows)}
    finally:
        conn.close()


# --- approvals (HITL decisions) -------------------------------------------


def record_approval(
    invoice_id: str,
    actor: str,
    decision: str,
    note: str = "",
    connection_id: str | None = None,
) -> dict:
    cid = connection_id or default_connection_id()
    conn = get_conn()
    try:
        row = conn.execute("SELECT COUNT(*) AS n FROM approvals").fetchone()
        approval_id = f"H-{int(row['n']) + 1:04d}"
        at = _now()
        payload = json.dumps(
            {
                "id": approval_id,
                "connectionId": cid,
                "transactionId": invoice_id,
                "actor": actor,
                "decision": decision,
                "note": note,
                "at": at,
            },
            ensure_ascii=False,
        )
        conn.execute(
            """
            INSERT INTO approvals
                (id, connection_id, transaction_id, at, actor, decision, note, payload)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (approval_id, cid, invoice_id, at, actor, decision, note, payload),
        )
        conn.commit()
        return json.loads(payload)
    finally:
        conn.close()


def list_approvals(connection_id: str | None = None, invoice_id: str | None = None) -> list[dict]:
    cid = connection_id or default_connection_id()
    conn = get_conn()
    try:
        sql = "SELECT payload FROM approvals WHERE connection_id = ?"
        params: list = [cid]
        if invoice_id:
            sql += " AND transaction_id = ?"
            params.append(invoice_id)
        sql += " ORDER BY rowid DESC"
        return [json.loads(r["payload"]) for r in conn.execute(sql, tuple(params)).fetchall()]
    finally:
        conn.close()


# --- source documents (hash + optional encryption + retention) ------------


def _encrypt(data: bytes, key_material: str) -> tuple[str | None, str | None]:
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except Exception:  # noqa: BLE001 - encryption is optional
        return None, None
    try:
        raw = base64.b64decode(key_material)
    except Exception:  # noqa: BLE001
        raw = b""
    if len(raw) not in (16, 24, 32):
        raw = hashlib.sha256((key_material or "").encode("utf-8")).digest()
    nonce = os.urandom(12)
    ciphertext = AESGCM(raw).encrypt(nonce, data, None)
    return (
        base64.b64encode(ciphertext).decode("ascii"),
        base64.b64encode(nonce).decode("ascii"),
    )


def store_document(
    invoice_id: str,
    text: str,
    connection_id: str | None = None,
    retention_days: int | None = None,
) -> dict:
    """Persist the source document's hash, plus ciphertext if a key is set."""
    from . import config

    cid = connection_id or default_connection_id()
    data = (text or "").encode("utf-8")
    digest = hashlib.sha256(data).hexdigest()
    cipher = nonce = None
    if config.DB_ENCRYPTION_KEY:
        cipher, nonce = _encrypt(data, config.DB_ENCRYPTION_KEY)
    created = _now()
    days = config.DOCUMENT_RETENTION_DAYS if retention_days is None else retention_days
    retention = (datetime.now(timezone.utc) + timedelta(days=days)).replace(microsecond=0).isoformat()
    doc_id = f"D-{digest[:12]}"
    conn = get_conn()
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO documents
                (id, connection_id, transaction_id, sha256, cipher, nonce, created_at, retention_until)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (doc_id, cid, invoice_id, digest, cipher, nonce, created, retention),
        )
        conn.commit()
    finally:
        conn.close()
    return {
        "id": doc_id,
        "sha256": digest,
        "encrypted": cipher is not None,
        "retentionUntil": retention,
    }


def get_document(invoice_id: str, connection_id: str | None = None) -> dict | None:
    cid = connection_id or default_connection_id()
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT sha256, cipher, nonce, created_at, retention_until FROM documents"
            " WHERE connection_id = ? AND transaction_id = ? ORDER BY rowid DESC LIMIT 1",
            (cid, invoice_id),
        ).fetchone()
        if not row:
            return None
        return {
            "sha256": row["sha256"],
            "encrypted": row["cipher"] is not None,
            "createdAt": row["created_at"],
            "retentionUntil": row["retention_until"],
        }
    finally:
        conn.close()


def purge_expired_documents(connection_id: str | None = None) -> int:
    """Drop stored ciphertext past its retention date (keep only the hash)."""
    cid = connection_id or default_connection_id()
    now = _now()
    conn = get_conn()
    try:
        cur = conn.execute(
            "UPDATE documents SET cipher = NULL, nonce = NULL"
            " WHERE connection_id = ? AND cipher IS NOT NULL"
            " AND retention_until IS NOT NULL AND retention_until < ?",
            (cid, now),
        )
        conn.commit()
        return int(cur.rowcount or 0)
    finally:
        conn.close()


# --- settings -------------------------------------------------------------


def get_settings() -> AppSettings:
    conn = get_conn()
    try:
        row = conn.execute("SELECT payload FROM kv WHERE key = 'settings'").fetchone()
        return AppSettings.model_validate_json(row["payload"]) if row else AppSettings()
    finally:
        conn.close()


def save_settings(settings: AppSettings) -> AppSettings:
    conn = get_conn()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO kv (key, payload) VALUES ('settings', ?)",
            (settings.model_dump_json(by_alias=True),),
        )
        conn.commit()
        return settings
    finally:
        conn.close()


def reset() -> None:
    conn = get_conn()
    try:
        conn.executescript(
            "DELETE FROM transactions; DELETE FROM audit; DELETE FROM approvals;"
            " DELETE FROM documents; DELETE FROM kv;"
        )
        conn.commit()
    finally:
        conn.close()
