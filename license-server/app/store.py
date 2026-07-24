"""Durable license store (SQLite). Records every issued key so a buyer can
re-fetch it, so you can revoke it, and so duplicate webhook deliveries are
idempotent (Gumroad/Payhip may deliver the same sale more than once).
"""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class LicenseRecord:
    sale_id: str
    provider: str          # "gumroad" | "payhip" | "manual"
    tier: str
    email: str
    key: str
    created_at: int
    revoked: int = 0


_SCHEMA = """
CREATE TABLE IF NOT EXISTS licenses (
    sale_id     TEXT PRIMARY KEY,
    provider    TEXT NOT NULL,
    tier        TEXT NOT NULL,
    email       TEXT NOT NULL,
    key         TEXT NOT NULL,
    created_at  INTEGER NOT NULL,
    revoked     INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_licenses_email ON licenses(email);
CREATE INDEX IF NOT EXISTS idx_licenses_key ON licenses(key);
"""


class LicenseStore:
    def __init__(self, path: str = "licenses.db") -> None:
        self.path = path
        # check_same_thread=False so the ASGI worker can share the connection.
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def get_by_sale(self, sale_id: str) -> Optional[LicenseRecord]:
        row = self._conn.execute(
            "SELECT * FROM licenses WHERE sale_id = ?", (sale_id,)
        ).fetchone()
        return self._row(row)

    def get_by_key(self, key: str) -> Optional[LicenseRecord]:
        row = self._conn.execute(
            "SELECT * FROM licenses WHERE key = ?", (key,)
        ).fetchone()
        return self._row(row)

    def upsert(self, rec: LicenseRecord) -> LicenseRecord:
        self._conn.execute(
            """INSERT INTO licenses (sale_id, provider, tier, email, key, created_at, revoked)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(sale_id) DO UPDATE SET
                 tier=excluded.tier, email=excluded.email, key=excluded.key""",
            (rec.sale_id, rec.provider, rec.tier, rec.email, rec.key,
             rec.created_at, rec.revoked),
        )
        self._conn.commit()
        return rec

    def revoke(self, key: str) -> bool:
        cur = self._conn.execute(
            "UPDATE licenses SET revoked = 1 WHERE key = ?", (key,)
        )
        self._conn.commit()
        return cur.rowcount > 0

    @staticmethod
    def _row(row: Optional[sqlite3.Row]) -> Optional[LicenseRecord]:
        if row is None:
            return None
        return LicenseRecord(**{k: row[k] for k in row.keys()})


def now() -> int:
    return int(time.time())
