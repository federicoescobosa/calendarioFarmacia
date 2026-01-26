from __future__ import annotations

from dataclasses import dataclass
from typing import List

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from farmacia_app.data.hardcoded import Employee, get_demo_employees, get_demo_week_schedule


DAYS = ["L", "M", "X", "J", "V", "S", "D"]


@dataclass
class Coverage:
    day: str
    tardes: int
    objetivo: int = 4


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Farmacia - Calendario semanal (demo hardcode)")
        self.resize(1100, 650)

        self._dirty = False
        self._employees: List[Employee] = get_demo_employees()
        self._schedule = get_demo_week_schedule()

        self._build_ui()
        self._load_table()

    def _build_ui(self) -> None:
        toolbar = QToolBar("Semana")
        self.addToolBar(toolbar)

        self.btn_prev = QPushButton("‹ Semana")
        self.btn_today = QPushButton("Semana actual")
        self.btn_next = QPushButton("Semana ›")
        self.lbl_week = QLabel("Semana demo (01/01/2026 - 07/01/2026)")
        self.lbl_week.setAlignment(Qt.AlignCenter)

        toolbar.addWidget(self.btn_prev)
        toolbar.addWidget(self.btn_today)
        toolbar.addWidget(self.btn_next)
        toolbar.addSeparator()
        toolbar.addWidget(self.lbl_week)

        self.btn_prev.clicked.connect(lambda: self._toast("Demo: navegación desactivada"))
        self.btn_today.clicked.connect(lambda: self._toast("Demo: navegación desactivada"))
        self.btn_next.clicked.connect(lambda: self._toast("Demo: navegación desactivada"))

        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        header_row = QHBoxLayout()
        self.lbl_dirty = QLabel("● Cambios sin guardar")
        self.lbl_dirty.setStyleSheet("font-weight:600; color:#b00020;")
        self.lbl_dirty.setVisible(False)

        self.btn_save = QPushButton("Guardar")
        self.btn_save.clicked.connect(self._on_save)

        header_row.addWidget(self.lbl_dirty)
        header_row.addStretch(1)
        header_row.addWidget(self.btn_save)
        root.addLayout(header_row)

        self.table = QTableWidget()
        self.table.setColumnCount(1 + len(DAYS))  # Empleado + 7 días
        self.table.setHorizontalHeaderLabels(["Empleado"] + DAYS)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.DoubleClicked | QTableWidget.EditKeyPressed)
        self.table.itemChanged.connect(self._on_item_changed)
        root.addWidget(self.table)

        self.lbl_footer = QLabel("")
        self.lbl_footer.setAlignment(Qt.AlignLeft)
        root.addWidget(self.lbl_footer)

        self.setCentralWidget(central)

    def _load_table(self) -> None:
        self.table.blockSignals(True)

        self.table.setRowCount(len(self._employees))
        for r, emp in enumerate(self._employees):
            name_item = QTableWidgetItem(f"{emp.code} - {emp.name}")
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(r, 0, name_item)

            week = self._schedule.get(emp.code, ["L"] * 7)
            for c, value in enumerate(week, start=1):
                it = QTableWidgetItem(value)
                it.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(r, c, it)

        self.table.resizeColumnsToContents()
        self.table.blockSignals(False)

        self._update_footer()

    def _compute_coverage(self) -> List[Coverage]:
        cover = []
        # Columnas 1..7 son días
        for day_idx, day in enumerate(DAYS, start=1):
            tardes = 0
            for r in range(self.table.rowCount()):
                v = (self.table.item(r, day_idx).text() or "").strip().upper()
                if v == "T":
                    tardes += 1
            cover.append(Coverage(day=day, tardes=tardes))
        return cover

    def _update_footer(self) -> None:
        cover = self._compute_coverage()
        chunks = [f"{c.day}: Tarde {c.tardes}/{c.objetivo}" for c in cover]
        self.lbl_footer.setText("Cobertura tardes (demo):  " + "   |   ".join(chunks))

    def _set_dirty(self, dirty: bool) -> None:
        self._dirty = dirty
        self.lbl_dirty.setVisible(dirty)

    def _on_item_changed(self, _item: QTableWidgetItem) -> None:
        # En demo, cualquier cambio marca dirty y actualiza cobertura
        self._set_dirty(True)
        self._update_footer()

    def _on_save(self) -> None:
        if not self._dirty:
            self._toast("Nada que guardar (demo).")
            return
        # Demo: no persistimos, solo “simulamos”
        self._set_dirty(False)
        self._toast("Guardado (demo).")

    def closeEvent(self, event) -> None:  # type: ignore[override]
        if self._dirty:
            res = QMessageBox.question(
                self,
                "Salir",
                "Hay cambios sin guardar (demo). ¿Salir igualmente?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if res == QMessageBox.No:
                event.ignore()
                return
        event.accept()

    def _toast(self, msg: str) -> None:
        QMessageBox.information(self, "Info", msg)
