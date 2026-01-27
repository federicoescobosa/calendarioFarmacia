from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Iterable, Optional, Tuple


# ----------------------------
# Modelo
# ----------------------------

@dataclass(frozen=True)
class Absence:
    employee_code: str           # "A", "B", "C"... o el identificador que uses
    type_code: str               # "VAC", "AP", "MAT", ...
    start: date
    end: date
    part: str = "FULL"           # "FULL" | "AM" | "PM"
    notes: str = ""


# ----------------------------
# Política (topes / reglas)
# ----------------------------

@dataclass(frozen=True)
class AbsencePolicy:
    # Vacaciones: tope anual en días naturales (mínimo legal: 30)
    vacation_days_per_year: float = 30.0

    # Asuntos propios: según convenio, 2 días/año
    asuntos_propios_days_per_year: float = 2.0


def validate_new_absence(
    new_absence: Absence,
    existing: Iterable[Absence],
    policy: AbsencePolicy = AbsencePolicy(),
) -> Tuple[bool, str]:
    """
    Valida el alta de una ausencia contra el histórico existente.
    Devuelve (ok, mensaje). Si ok=False, el mensaje es el motivo.
    """

    # Básicos
    if new_absence.end < new_absence.start:
        return False, "La fecha fin no puede ser anterior a la fecha inicio."

    if new_absence.part not in ("FULL", "AM", "PM"):
        return False, "Parte inválida (usa FULL, AM o PM)."

    # Si es medio día, solo tiene sentido si start == end
    if new_absence.part in ("AM", "PM") and new_absence.start != new_absence.end:
        return False, "Las ausencias de medio día deben ser de un solo día (inicio = fin)."

    # Evitar solapes por trabajador
    for a in existing:
        if a.employee_code != new_absence.employee_code:
            continue
        if _overlaps(a, new_absence):
            return False, "Esta ausencia solapa con otra ausencia existente del trabajador."

    # Reglas por tipo
    code = new_absence.type_code.upper().strip()

    if code == "VAC":
        return _validate_vacations(new_absence, existing, policy)

    if code == "AP":  # Asuntos propios
        return _validate_asuntos_propios(new_absence, existing, policy)

    # Por defecto: sin tope (de momento)
    return True, "OK"


# ----------------------------
# Reglas específicas
# ----------------------------

def _validate_vacations(
    new_absence: Absence,
    existing: Iterable[Absence],
    policy: AbsencePolicy
) -> Tuple[bool, str]:
    # Calcula por año natural (si cruza años, se reparte)
    years = range(new_absence.start.year, new_absence.end.year + 1)
    for y in years:
        used = 0.0
        for a in existing:
            if a.employee_code != new_absence.employee_code:
                continue
            if a.type_code.upper().strip() != "VAC":
                continue
            used += _units_in_year(a, y)

        used_after = used + _units_in_year(new_absence, y)
        limit = policy.vacation_days_per_year

        if used_after > limit + 1e-9:
            remaining = max(0.0, limit - used)
            return (
                False,
                f"Vacaciones excedidas en {y}: límite {limit:g} días/año. "
                f"Ya usados {used:g}. Te quedan {remaining:g}."
            )

    return True, "OK"


def _validate_asuntos_propios(
    new_absence: Absence,
    existing: Iterable[Absence],
    policy: AbsencePolicy
) -> Tuple[bool, str]:
    # Se limita por año natural del inicio (lo normal para AP)
    y = new_absence.start.year
    used = 0.0
    for a in existing:
        if a.employee_code != new_absence.employee_code:
            continue
        if a.type_code.upper().strip() != "AP":
            continue
        # AP: si cruza año (no debería), cuenta por el año de cada día
        used += _units_in_year(a, y)

    used_after = used + _units_in_year(new_absence, y)
    limit = policy.asuntos_propios_days_per_year

    if used_after > limit + 1e-9:
        remaining = max(0.0, limit - used)
        return (
            False,
            f"Asuntos propios excedidos en {y}: límite {limit:g} días/año. "
            f"Ya usados {used:g}. Te quedan {remaining:g}."
        )

    return True, "OK"


# ----------------------------
# Helpers
# ----------------------------

def _overlaps(a: Absence, b: Absence) -> bool:
    # Solape por fecha (incluyente)
    if a.end < b.start or b.end < a.start:
        return False

    # Si ambos son medio día en el mismo día: AM no solapa con PM
    if a.start == a.end == b.start == b.end:
        if a.part in ("AM", "PM") and b.part in ("AM", "PM"):
            return a.part == b.part  # AM vs PM no solapa, AM vs AM sí
    return True


def _units_in_year(a: Absence, year: int) -> float:
    """
    Cuenta unidades (días naturales o 0.5) de una ausencia dentro de un año natural.
    - FULL: 1 por día
    - AM/PM: 0.5 (y solo si es un día)
    """
    start = max(a.start, date(year, 1, 1))
    end = min(a.end, date(year, 12, 31))
    if end < start:
        return 0.0

    if a.part in ("AM", "PM"):
        # medio día => solo un día (lo validamos arriba)
        return 0.5 if start == end else 0.0

    # FULL
    return float((end - start).days + 1)
