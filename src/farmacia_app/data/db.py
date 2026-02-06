from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Optional


APP_DIR_NAME = "calendarioFarmacia"
DB_FILENAME = "app.db"


def get_data_dir() -> Path:
    """
    Windows: %LOCALAPPDATA%\calendarioFarmacia\data
    Linux/macOS: ~/.local/share/calendarioFarmacia/data
    """
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        base = Path(local_app_data)
    else:
        base = Path.home() / ".local" / "share"

    data_dir = base / APP_DIR_NAME / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_db_path() -> Path:
    return get_data_dir() / DB_FILENAME


def connect(db_path: Optional[Path] = None) -> sqlite3.Connection:
    path = str(db_path or get_db_path())
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_schema(conn: sqlite3.Connection) -> None:
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
    conn.commit()
