from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import List


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


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    cur = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1;",
        (table,),
    )
    return cur.fetchone() is not None


def _table_columns(conn: sqlite3.Connection, table: str) -> List[str]:
    cur = conn.execute(f"PRAGMA table_info({table});")
    return [str(r["name"]) for r in cur.fetchall()]


def _has_column(conn: sqlite3.Connection, table: str, column: str) -> bool:
    return column in _table_columns(conn, table)


def _first_existing(cols: List[str], candidates: List[str]) -> str | None:
    for c in candidates:
        if c in cols:
            return c
    return None


def _migrate_holiday_sync_if_needed(conn: sqlite3.Connection) -> None:
    if not _table_exists(conn, "holiday_sync"):
        return

    cols = _table_columns(conn, "holiday_sync")
    if "country_code" in cols:
        return  # ya está bien

    # Renombrar tabla legacy
    conn.execute("ALTER TABLE holiday_sync RENAME TO holiday_sync_legacy;")

    # Crear tabla nueva con el esquema actual
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

    legacy_cols = _table_columns(conn, "holiday_sync_legacy")

    # Mapeos tolerantes a nombres antiguos
    country_col = _first_existing(legacy_cols, ["country_code", "country", "countryIsoCode", "country_iso_code"])
    subdiv_col = _first_existing(legacy_cols, ["subdivision_code", "subdivision", "subdivisionCode", "subdivision_iso_code"])
    year_col = _first_existing(legacy_cols, ["year"])
    synced_col = _first_existing(legacy_cols, ["synced_at", "syncedAt", "fetched_at", "fetchedAt"])
    status_col = _first_existing(legacy_cols, ["status"])
    error_col = _first_existing(legacy_cols, ["error_message", "error", "errorMessage", "message"])

    # Si faltan columnas, insertamos lo que podamos sin reventar.
    # Nota: subdivision_code en la nueva tabla NO puede ser NULL.
    select_country = f"COALESCE({country_col}, 'ES')" if country_col else "'ES'"
    select_subdiv = f"COALESCE({subdiv_col}, '')" if subdiv_col else "''"
    select_year = f"COALESCE({year_col}, CAST(strftime('%Y','now') AS INTEGER))" if year_col else "CAST(strftime('%Y','now') AS INTEGER)"
    select_synced = f"COALESCE({synced_col}, datetime('now'))" if synced_col else "datetime('now')"
    select_status = f"COALESCE({status_col}, 'OK')" if status_col else "'OK'"
    select_error = f"COALESCE({error_col}, '')" if error_col else "''"

    conn.execute(
        f"""
        INSERT OR IGNORE INTO holiday_sync (country_code, subdivision_code, year, synced_at, status, error_message)
        SELECT
            {select_country},
            {select_subdiv},
            {select_year},
            {select_synced},
            {select_status},
            {select_error}
        FROM holiday_sync_legacy;
        """
    )

    conn.execute("DROP TABLE holiday_sync_legacy;")


def _migrate_holidays_if_needed(conn: sqlite3.Connection) -> None:
    if not _table_exists(conn, "holidays"):
        return

    cols = _table_columns(conn, "holidays")
    # Esquema esperado: date, name, country_code, subdivision_code, scope, source, fetched_at
    needed = {"date", "name", "country_code", "subdivision_code", "scope", "source", "fetched_at"}
    if needed.issubset(set(cols)):
        return  # ok

    # Renombrar tabla legacy
    conn.execute("ALTER TABLE holidays RENAME TO holidays_legacy;")

    # Crear tabla nueva
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

    legacy_cols = _table_columns(conn, "holidays_legacy")

    date_col = _first_existing(legacy_cols, ["date", "day"])
    name_col = _first_existing(legacy_cols, ["name", "local_name", "title"])
    country_col = _first_existing(legacy_cols, ["country_code", "country", "countryIsoCode", "country_iso_code"])
    subdiv_col = _first_existing(legacy_cols, ["subdivision_code", "subdivision", "subdivisionCode", "subdivision_iso_code"])
    scope_col = _first_existing(legacy_cols, ["scope", "type"])
    source_col = _first_existing(legacy_cols, ["source"])
    fetched_col = _first_existing(legacy_cols, ["fetched_at", "synced_at", "created_at"])

    # Defaults razonables
    select_date = date_col if date_col else "''"
    select_name = name_col if name_col else "''"
    select_country = f"COALESCE({country_col}, 'ES')" if country_col else "'ES'"
    select_subdiv = f"COALESCE({subdiv_col}, '')" if subdiv_col else "''"
    select_scope = f"COALESCE({scope_col}, 'NATIONAL')" if scope_col else "'NATIONAL'"
    select_source = f"COALESCE({source_col}, 'Legacy')" if source_col else "'Legacy'"
    select_fetched = f"COALESCE({fetched_col}, datetime('now'))" if fetched_col else "datetime('now')"

    conn.execute(
        f"""
        INSERT OR IGNORE INTO holidays (date, name, country_code, subdivision_code, scope, source, fetched_at)
        SELECT
            {select_date},
            {select_name},
            {select_country},
            {select_subdiv},
            {select_scope},
            {select_source},
            {select_fetched}
        FROM holidays_legacy;
        """
    )

    conn.execute("DROP TABLE holidays_legacy;")


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

    # IMPORTANTE: migraciones antes/además del create
    _migrate_holiday_sync_if_needed(conn)
    _migrate_holidays_if_needed(conn)

    # Si no existían, se crean aquí
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