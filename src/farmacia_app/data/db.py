from __future__ import annotations

import os
import sqlite3
from pathlib import Path


def _db_path() -> Path:
    """
    BD en AppData\Local\<App>\data\app.db (Windows).
    Si prefieres otra ubicación, cambia aquí.
    """
    base = Path(os.environ.get("LOCALAPPDATA", ".")) / "CalendarioFarmacia" / "data"
    base.mkdir(parents=True, exist_ok=True)
    return base / "app.db"


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def ensure_schema(conn: sqlite3.Connection) -> None:
    # --- Empleados ---
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS employees (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre     TEXT NOT NULL,
            apellido1  TEXT NOT NULL,
            apellido2  TEXT NOT NULL,
            dni        TEXT NOT NULL UNIQUE,
            is_owner   INTEGER NOT NULL DEFAULT 0
        );
        """
    )

    # --- Festivos cacheados ---
    # IMPORTANTE: subdivision_code NO puede ser NULL si lo usamos en PRIMARY KEY.
    # Usamos '' (cadena vacía) cuando no hay subdivisión.
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS holidays (
            date             TEXT NOT NULL,   -- YYYY-MM-DD
            name             TEXT NOT NULL,
            country_code      TEXT NOT NULL,  -- 'ES'
            subdivision_code  TEXT NOT NULL DEFAULT '', -- '' si no aplica
            scope             TEXT NOT NULL,  -- 'NATIONAL' | 'REGIONAL' | 'LOCAL'
            source            TEXT NOT NULL,  -- 'OpenHolidays'
            fetched_at        TEXT NOT NULL,  -- ISO datetime
            PRIMARY KEY (date, name, country_code, subdivision_code, scope)
        );
        """
    )

    # --- Control de sincronización por año ---
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS holiday_sync (
            country_code      TEXT NOT NULL,
            subdivision_code  TEXT NOT NULL,
            year              INTEGER NOT NULL,
            synced_at         TEXT NOT NULL,
            status            TEXT NOT NULL,  -- 'OK' | 'ERROR'
            error_message     TEXT,
            PRIMARY KEY (country_code, subdivision_code, year)
        );
        """
    )

    conn.commit()
