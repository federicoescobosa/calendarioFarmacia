from __future__ import annotations

from typing import Dict, List

from farmacia_app.data.db import connect, ensure_schema
from farmacia_app.ui.shared import TURN_ORDER


class WeeklyTemplateRepository:
    """
    Plantilla semanal por empleado.
    Tabla: weekly_template(employee_id, weekday, turn_code)
      - weekday: 0=L .. 6=D
    """

    def __init__(self) -> None:
        self._conn = connect()
        ensure_schema(self._conn)

    def load_all(self, employee_ids: List[int]) -> Dict[int, List[str]]:
        """
        Devuelve:
          { employee_id: [turn_L, turn_M, ..., turn_D] }

        Si no hay datos, devuelve por defecto ["L"]*7.
        """
        out: Dict[int, List[str]] = {int(eid): ["L"] * 7 for eid in employee_ids}
        if not employee_ids:
            return out

        placeholders = ",".join(["?"] * len(employee_ids))
        cur = self._conn.execute(
            f"""
            SELECT employee_id, weekday, turn_code
            FROM weekly_template
            WHERE employee_id IN ({placeholders})
            ORDER BY employee_id, weekday;
            """,
            [int(x) for x in employee_ids],
        )

        for row in cur.fetchall():
            emp_id = int(row["employee_id"])
            wd = int(row["weekday"])
            code = str(row["turn_code"]).strip().upper()
            if code not in TURN_ORDER:
                code = "L"
            if 0 <= wd <= 6:
                out.setdefault(emp_id, ["L"] * 7)[wd] = code

        return out

    def upsert(self, employee_id: int, weekday: int, turn_code: str) -> None:
        code = (turn_code or "L").strip().upper()
        if code not in TURN_ORDER:
            code = "L"
        self._conn.execute(
            """
            INSERT INTO weekly_template (employee_id, weekday, turn_code)
            VALUES (?, ?, ?)
            ON CONFLICT(employee_id, weekday) DO UPDATE SET turn_code=excluded.turn_code;
            """,
            (int(employee_id), int(weekday), code),
        )

    def upsert_week(self, employee_id: int, turns_7: List[str]) -> None:
        if len(turns_7) != 7:
            raise ValueError("turns_7 debe tener 7 elementos (L..D).")
        for wd in range(7):
            self.upsert(employee_id, wd, turns_7[wd])
        self._conn.commit()
