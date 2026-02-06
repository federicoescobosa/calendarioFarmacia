from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import List, Optional

from farmacia_app.data.db import connect, ensure_schema


@dataclass(frozen=True)
class EmployeeRow:
    id: int
    nombre: str
    apellido1: str
    apellido2: str
    dni: str
    is_owner: bool

    @property
    def full_name(self) -> str:
        return f"{self.nombre} {self.apellido1} {self.apellido2}".strip()


class EmployeeRepository:
    def __init__(self) -> None:
        self._conn = connect()
        ensure_schema(self._conn)
        self._ensure_owner()

    def _ensure_owner(self) -> None:
        # Dueño fijo inicial (si no existe)
        cur = self._conn.execute("SELECT id FROM employees WHERE is_owner = 1 LIMIT 1;")
        row = cur.fetchone()
        if row:
            return

        # DNI "OWNER" para garantizar NOT NULL y UNIQUE sin inventar un DNI real
        self._conn.execute(
            """
            INSERT OR IGNORE INTO employees (nombre, apellido1, apellido2, dni, is_owner)
            VALUES (?, ?, ?, ?, 1);
            """,
            ("Juan Jose", "", "", "OWNER"),
        )
        self._conn.commit()

    def list_all(self) -> List[EmployeeRow]:
        cur = self._conn.execute(
            """
            SELECT id, nombre, apellido1, apellido2, dni, is_owner
            FROM employees
            ORDER BY is_owner DESC, apellido1 ASC, apellido2 ASC, nombre ASC;
            """
        )
        out: List[EmployeeRow] = []
        for r in cur.fetchall():
            out.append(
                EmployeeRow(
                    id=int(r["id"]),
                    nombre=str(r["nombre"]),
                    apellido1=str(r["apellido1"]),
                    apellido2=str(r["apellido2"]),
                    dni=str(r["dni"]),
                    is_owner=bool(int(r["is_owner"])),
                )
            )
        return out

    def get_by_id(self, emp_id: int) -> Optional[EmployeeRow]:
        cur = self._conn.execute(
            """
            SELECT id, nombre, apellido1, apellido2, dni, is_owner
            FROM employees
            WHERE id = ?;
            """,
            (emp_id,),
        )
        r = cur.fetchone()
        if not r:
            return None
        return EmployeeRow(
            id=int(r["id"]),
            nombre=str(r["nombre"]),
            apellido1=str(r["apellido1"]),
            apellido2=str(r["apellido2"]),
            dni=str(r["dni"]),
            is_owner=bool(int(r["is_owner"])),
        )

    def create(self, nombre: str, apellido1: str, apellido2: str, dni: str) -> EmployeeRow:
        dni = dni.strip().upper()
        if not dni:
            raise ValueError("El DNI es obligatorio.")

        try:
            cur = self._conn.execute(
                """
                INSERT INTO employees (nombre, apellido1, apellido2, dni, is_owner)
                VALUES (?, ?, ?, ?, 0);
                """,
                (nombre.strip(), apellido1.strip(), apellido2.strip(), dni),
            )
            self._conn.commit()
        except sqlite3.IntegrityError as e:
            raise ValueError("Ya existe un empleado con ese DNI.") from e

        emp_id = int(cur.lastrowid)
        emp = self.get_by_id(emp_id)
        assert emp is not None
        return emp

    def update(self, emp_id: int, nombre: str, apellido1: str, apellido2: str, dni: str) -> EmployeeRow:
        dni = dni.strip().upper()
        if not dni:
            raise ValueError("El DNI es obligatorio.")

        emp = self.get_by_id(emp_id)
        if not emp:
            raise ValueError("Empleado no encontrado.")

        # No permitir cambiar el DNI del dueño si lo tienes como OWNER (opcional)
        if emp.is_owner:
            dni = emp.dni

        try:
            self._conn.execute(
                """
                UPDATE employees
                SET nombre = ?, apellido1 = ?, apellido2 = ?, dni = ?
                WHERE id = ?;
                """,
                (nombre.strip(), apellido1.strip(), apellido2.strip(), dni, emp_id),
            )
            self._conn.commit()
        except sqlite3.IntegrityError as e:
            raise ValueError("Ya existe un empleado con ese DNI.") from e

        updated = self.get_by_id(emp_id)
        assert updated is not None
        return updated

    def delete(self, emp_id: int) -> None:
        emp = self.get_by_id(emp_id)
        if not emp:
            return
        if emp.is_owner:
            raise ValueError("No se puede borrar el dueño.")
        self._conn.execute("DELETE FROM employees WHERE id = ?;", (emp_id,))
        self._conn.commit()
