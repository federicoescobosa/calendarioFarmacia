from __future__ import annotations

import os
import sqlite3
from pathlib import Path


def _db_path() -> Path:
    """
    BD en AppData\\Local\\CalendarioFarmacia\\data\\app.db (Windows).
    """
    base = Path(os.environ.get("LOCALAPPDATA", ".")) / "CalendarioFarmacia" / "data"
    base.mkdir(parents=True, exist_ok=True)
    return base / "app.db"


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def _has_column(conn: sqlite3.Connection, table: str, column: str) -> bool:
    cur = conn.execute(f"PRAGMA table_info({table});")
    cols = [str(r["name"]) for r in cur.fetchall()]
    return column in cols


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS employees (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre     TEXT NOT NULL,
            apellido1  TEXT NOT NULL,
            apellido2  TEXT NOT NULL,
            dni        TEXT NOT NULL UNIQUE,
            is_owner   INTEGER NOT NULL DEFAULT 0,
            email      TEXT NOT NULL DEFAULT '',
            role       TEXT NOT NULL DEFAULT 'Empleado'
        );
        """
    )

    if not _has_column(conn, "employees", "email"):
        conn.execute("ALTER TABLE employees ADD COLUMN email TEXT NOT NULL DEFAULT '';")
    if not _has_column(conn, "employees", "role"):
        conn.execute("ALTER TABLE employees ADD COLUMN role TEXT NOT NULL DEFAULT 'Empleado';")

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS employee_allowed_turns (
            employee_id INTEGER NOT NULL,
            turn_code   TEXT NOT NULL,
            PRIMARY KEY (employee_id, turn_code),
            FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
        );
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS weekly_template (
            employee_id INTEGER NOT NULL,
            weekday     INTEGER NOT NULL,
            turn_code   TEXT NOT NULL,
            PRIMARY KEY (employee_id, weekday),
            FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
        );
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schedule (
            employee_id INTEGER NOT NULL,
            day         TEXT NOT NULL,
            turn_code   TEXT NOT NULL,
            PRIMARY KEY (employee_id, day),
            FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
        );
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS holiday_sync (
            country_code      TEXT NOT NULL,
            subdivision_code  TEXT NOT NULL DEFAULT '',
            year              INTEGER NOT NULL,
            synced_at         TEXT NOT NULL,
            status            TEXT NOT NULL,
            error_message     TEXT NOT NULL DEFAULT '',
            PRIMARY KEY (country_code, subdivision_code, year)
        );
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS holidays (
            date              TEXT NOT NULL,
            name              TEXT NOT NULL,
            country_code      TEXT NOT NULL,
            subdivision_code  TEXT NOT NULL DEFAULT '',
            scope             TEXT NOT NULL,
            source            TEXT NOT NULL,
            fetched_at        TEXT NOT NULL,
            PRIMARY KEY (date, country_code, subdivision_code, scope)
        );
        """
    )

    conn.commit()
