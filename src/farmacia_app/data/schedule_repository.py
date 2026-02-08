from __future__ import annotations

from datetime import date, timedelta
from typing import Dict, List

from farmacia_app.data.db import connect, ensure_schema


class ScheduleRepository:
    def __init__(self) -> None:
        self._conn = connect()
        ensure_schema(self._conn)

    def load_week(self, employee_ids: List[int], week_start: date) -> Dict[int, List[str]]:
        """
        Devuelve:
          { employee_id: [turn_L, turn_M, ..., turn_D] }
        Si no hay dato en BD para un día -> no se rellena aquí (el caller decide default).
        """
        week_end = week_start + timedelta(days=6)
        emp_set = set(int(x) for x in employee_ids)
        if not emp_set:
            return {}

        # Construimos placeholders (?, ?, ...) para IN
        placeholders = ",".join(["?"] * len(emp_set))
        params = [week_start.isoformat(), week_end.isoformat(), *emp_set]

        cur = self._conn.execute(
            f"""
            SELECT employee_id, day, turn_code
            FROM schedule
            WHERE day BETWEEN ? AND ?
              AND employee_id IN ({placeholders})
            ORDER BY employee_id, day;
            """,
            params,
        )

        out: Dict[int, List[str]] = {}
        for row in cur.fetchall():
            emp_id = int(row["employee_id"])
            d = date.fromisoformat(str(row["day"]))
            idx = (d - week_start).days
            if idx < 0 or idx > 6:
                continue
            out.setdefault(emp_id, [""] * 7)[idx] = str(row["turn_code"])
        return out

    def upsert_week(self, employee_id: int, week_start: date, turns_7: List[str]) -> None:
        if len(turns_7) != 7:
            raise ValueError("turns_7 debe tener 7 elementos (L..D).")

        for i in range(7):
            d = week_start + timedelta(days=i)
            code = (turns_7[i] or "L").strip().upper()
            self._conn.execute(
                """
                INSERT INTO schedule (employee_id, day, turn_code)
                VALUES (?, ?, ?)
                ON CONFLICT(employee_id, day) DO UPDATE SET turn_code=excluded.turn_code;
                """,
                (int(employee_id), d.isoformat(), code),
            )

        self._conn.commit()
