from __future__ import annotations

from typing import Dict, List

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from farmacia_app.data.employee_repository import EmployeeRepository, EmployeeRow
from farmacia_app.data.weekly_template_repository import WeeklyTemplateRepository
from farmacia_app.ui.shared import DAYS, TURN_ORDER


class RulesDialog(QDialog):
    """
    Reglas = PLANTILLA SEMANAL (asignación base).
    Lo que se marca aquí DEBE verse en el calendario.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Reglas - Plantilla semanal")
        self.setModal(True)

        # Repos
        self._employees_repo = EmployeeRepository()
        self._template_repo = WeeklyTemplateRepository()

        self._employees: List[EmployeeRow] = self._employees_repo.list_all()
        emp_ids = [e.id for e in self._employees]
        self._templates: Dict[int, List[str]] = self._template_repo.load_all(emp_ids)

        # UI
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        title = QLabel("Plantilla semanal por empleado")
        title.setStyleSheet("font-size: 18px; font-weight: 700;")
        subtitle = QLabel(
            "Define el turno base de cada empleado para cada día (L..D). "
            "Estos valores se usan para rellenar el calendario cuando no hay turnos guardados en la semana."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color:#555;")
        root.addWidget(title)
        root.addWidget(subtitle)

        self.table = QTableWidget()
        self.table.setColumnCount(1 + len(DAYS))
        self.table.setHorizontalHeaderLabels(["Empleado"] + DAYS)
        self.table.verticalHeader().setVisible(False)
        self.table.setRowCount(len(self._employees))
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setStyleSheet(
            """
            QTableWidget {
                font-size: 13px;
            }
            QHeaderView::section {
                background: #f5f5f5;
                padding: 6px;
                border: 1px solid #d0d0d0;
                font-weight: 600;
            }
            """
        )

        # Fill rows
        for r, emp in enumerate(self._employees):
            name = emp.full_name if emp.full_name.strip() else emp.nombre
            it = QTableWidgetItem(name)
            it.setFlags(it.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(r, 0, it)

            week = self._templates.get(emp.id, ["L"] * 7)
            for c in range(7):
                combo = QComboBox()
                combo.addItems(TURN_ORDER)
                cur = (week[c] or "L").strip().upper()
                combo.setCurrentText(cur if cur in TURN_ORDER else "L")
                combo.setMinimumWidth(90)
                self.table.setCellWidget(r, 1 + c, combo)

        root.addWidget(self.table, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        # Tamaño grande + centrado
        self.resize(980, 620)
        self._center_on_parent()

    def _center_on_parent(self) -> None:
        parent = self.parentWidget()
        if parent is None:
            screen = self.screen()
            if screen is None:
                return
            geo = screen.availableGeometry()
        else:
            geo = parent.frameGeometry()

        g = self.frameGeometry()
        g.moveCenter(geo.center())
        self.move(g.topLeft())

    def _on_save(self) -> None:
        # Guardamos por empleado, semana (7 días)
        for r, emp in enumerate(self._employees):
            turns_7: List[str] = []
            for c in range(7):
                w = self.table.cellWidget(r, 1 + c)
                if isinstance(w, QComboBox):
                    turns_7.append((w.currentText() or "L").strip().upper())
                else:
                    turns_7.append("L")
            self._template_repo.upsert_week(emp.id, turns_7)

        self.accept()
