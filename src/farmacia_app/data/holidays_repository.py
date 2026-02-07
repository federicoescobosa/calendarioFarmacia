from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, date
from typing import List, Optional

from farmacia_app.data.db import connect, ensure_schema
from farmacia_app.data.openholidays_client import fetch_public_holidays


@dataclass(frozen=True)
class HolidayRow:
    date: str
    name: str
    country_code: str
    subdivision_code: Optional[str]
    scope: str  # NATIONAL/REGIONAL/LOCAL


class HolidaysRepository:
    def __init__(self) -> None:
        self._conn = connect()
        ensure_schema(self._conn)

    def has_sync(self, *, country_code: str, subdivision_code: str, year: int) -> bool:
        cur = self._conn.execute(
            """
            SELECT 1 FROM holiday_sync
            WHERE country_code = ? AND subdivision_code = ? AND year = ? AND status = 'OK'
            LIMIT 1;
            """,
            (country_code, subdivision_code, year),
        )
        return cur.fetchone() is not None

    def mark_sync(self, *, country_code: str, subdivision_code: str, year: int, ok: bool, error: Optional[str] = None) -> None:
        self._conn.execute(
            """
            INSERT INTO holiday_sync (country_code, subdivision_code, year, synced_at, status, error_message)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(country_code, subdivision_code, year)
            DO UPDATE SET synced_at=excluded.synced_at, status=excluded.status, error_message=excluded.error_message;
            """,
            (
                country_code,
                subdivision_code,
                year,
                datetime.now().isoformat(timespec="seconds"),
                "OK" if ok else "ERROR",
                error,
            ),
        )
        self._conn.commit()

    def upsert_many(self, rows: List[HolidayRow]) -> None:
        now = datetime.now().isoformat(timespec="seconds")
        for r in rows:
            self._conn.execute(
    """
    INSERT OR REPLACE INTO holidays (date, name, country_code, subdivision_code, scope, source, fetched_at)
    VALUES (?, ?, ?, ?, ?, 'OpenHolidays', ?);
    """,
    (r.date, r.name, r.country_code, (r.subdivision_code or ""), r.scope, now),
)

        self._conn.commit()

    def is_holiday(self, *, day: date, country_code: str, subdivision_code: str) -> bool:
        d = day.isoformat()
        cur = self._conn.execute(
    """
    SELECT 1
    FROM holidays
    WHERE date = ?
      AND country_code = ?
      AND (
            scope = 'NATIONAL'
            OR (scope = 'REGIONAL' AND subdivision_code = ?)
          )
    LIMIT 1;
    """,
    (d, country_code, subdivision_code),
)

        return cur.fetchone() is not None

    def holiday_name(self, *, day: date, country_code: str, subdivision_code: str) -> Optional[str]:
        d = day.isoformat()
        cur = self._conn.execute(
            """
            SELECT name
            FROM holidays
            WHERE date = ?
              AND country_code = ?
              AND (
                    scope = 'NATIONAL'
                    OR (scope = 'REGIONAL' AND subdivision_code = ?)
                  )
            ORDER BY scope DESC
            LIMIT 1;
            """,
            (d, country_code, subdivision_code),
        )
        row = cur.fetchone()
        return str(row["name"]) if row else None

    def ensure_year(self, *, country_code: str, subdivision_code: str, year: int) -> None:
        if self.has_sync(country_code=country_code, subdivision_code=subdivision_code, year=year):
            return

        valid_from = f"{year}-01-01"
        valid_to = f"{year}-12-31"

        try:
            holidays = fetch_public_holidays(
                country_code=country_code,
                subdivision_code=subdivision_code,
                valid_from=valid_from,
                valid_to=valid_to,
                language_iso_code="ES",
            )

            rows: List[HolidayRow] = []
            for h in holidays:
                # Si viene con subdivision_code => REGIONAL; si no => NATIONAL
                scope = "REGIONAL" if h.subdivision_code else "NATIONAL"
                rows.append(
                    HolidayRow(
                        date=h.date,
                        name=h.name,
                        country_code=country_code,
                        subdivision_code=h.subdivision_code,
                        scope=scope,
                    )
                )

            self.upsert_many(rows)
            self.mark_sync(country_code=country_code, subdivision_code=subdivision_code, year=year, ok=True)

        except Exception as ex:
            # No bloqueamos arranque
            self.mark_sync(country_code=country_code, subdivision_code=subdivision_code, year=year, ok=False, error=str(ex))
