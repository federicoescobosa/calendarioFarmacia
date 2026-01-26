from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class Employee:
    code: str
    name: str


# Turnos demo (hardcode)
# M = Mañana, T = Tarde, L = Libre, G = Guardia (demo)
Schedule = Dict[str, List[str]]  # employee_code -> 7 valores (L..D)


def get_demo_employees() -> List[Employee]:
    return [
        Employee(code="A", name="Encarni"),
        Employee(code="B", name="María"),
        Employee(code="C", name="Fátima"),
        Employee(code="D", name="Belén"),
        Employee(code="E", name="Thalisa"),
        Employee(code="X", name="Dueño"),
    ]


def get_demo_week_schedule() -> Schedule:
    # 7 días: L M X J V S D
    # Esto es solo para validar UI (habrá errores a propósito para ver alertas/cobertura)
    return {
        "A": ["M", "M", "M", "M", "M", "L", "L"],
        "B": ["M", "M", "M", "M", "M", "L", "L"],
        "C": ["T", "T", "T", "T", "T", "L", "L"],
        "D": ["T", "T", "T", "T", "T", "T", "L"],
        "E": ["M", "M", "M", "M", "M", "T", "T"],
        # Dueño: 2 tardes libres (demo)
        "X": ["T", "L", "T", "L", "T", "L", "L"],
    }
