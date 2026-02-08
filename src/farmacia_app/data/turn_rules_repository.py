from __future__ import annotations

from typing import Dict, Set

from farmacia_app.data.db import connect, ensure_schema


class TurnRulesRepository:
    """
    Persistencia de turnos permitidos por empleado.
    Tabla: employee_allowed_turns(employee_id, turn_code)
    """

    def __init__(self) -> None:
        self._conn = connect()
        ensure_schema(self._conn)

    def get_allowed_turns_by_employee(self) -> Dict[int, Set[str]]:
        cur = self._conn.execute(
            """
            SELECT employee_id, turn_code
            FROM employee_allowed_turns
            ORDER BY employee_id, turn_code;
            """
        )
        out: Dict[int, Set[str]] = {}
        for r in cur.fetchall():
            emp_id = int(r["employee_id"])
            code = str(r["turn_code"])
            out.setdefault(emp_id, set()).add(code)
        return out

    def set_allowed_turns(self, employee_id: int, allowed: Set[str]) -> None:
        self._conn.execute("DELETE FROM employee_allowed_turns WHERE employee_id = ?;", (employee_id,))
        for code in sorted(allowed):
            self._conn.execute(
                "INSERT INTO employee_allowed_turns (employee_id, turn_code) VALUES (?, ?);",
                (employee_id, code),
            )
        self._conn.commit()
