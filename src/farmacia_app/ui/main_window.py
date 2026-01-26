from __future__ import annotations

from dataclasses import dataclass
from typing import List

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor
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
    QHeaderView,
    QSizePolicy,
)

from farmacia_app.data.hardcoded import Employee, get_demo_employees, get_demo_week_schedule


DAYS = ["L", "M", "X", "J", "V", "S", "D"]

TURN_LABEL = {
    "M": "Mañana",
    "T": "Tarde",
    "L": "Libre",
    "G": "Guardia",
}

TURN_HOURS = {
    "M": "Mañana: 08:30–14:30 (aprox.)",
    "T": "Tarde: 17:00–20:30 (aprox.)",
    "L": "Libre: no trabaja",
    "G": "Guardia: pendiente de concretar (horario/compensación)",
}

TURN_BG = {
    "M": "#DDEBFF",  # azul claro
    "T": "#FFE6CC",  # naranja claro
    "L": "#F2F2F2",  # gris claro
    "G": "#E8D9FF",  # violeta claro
}

TURN_FG = {
    "M": "#1F4E79",
    "T": "#7A3E00",
    "L": "#444444",
    "G": "#4A2A7A",
}


@dataclass
class Coverage:
    day: str
    tardes: int
    objetivo: int = 4


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Farmacia - Calendario semanal (demo hardcode)")
        self.resize(1200, 700)

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

        # Barra superior (dirty + guardar)
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

        # Leyenda
        root.addLayout(self._build_legend())

        # Tabla
        self.table = QTableWidget()
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.table.setColumnCount(1 + len(DAYS))
        self.table.setHorizontalHeaderLabels(["Empleado"] + DAYS)
        self.table.verticalHeader().setVisible(False)

        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(True)
        self.table.setStyleSheet(
            """
            QTableWidget {
                gridline-color: #d0d0d0;
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

        h = self.table.horizontalHeader()
        h.setSectionResizeMode(QHeaderView.Stretch)
        h.setStretchLastSection(True)

        self.table.setColumnWidth(0, 240)
        self.table.verticalHeader().setDefaultSectionSize(34)

        self.table.setEditTriggers(QTableWidget.DoubleClicked | QTableWidget.EditKeyPressed)
        self.table.itemChanged.connect(self._on_item_changed)

        root.addWidget(self.table)

        self.lbl_footer = QLabel("")
        self.lbl_footer.setAlignment(Qt.AlignLeft)
        self.lbl_footer.setStyleSheet("color:#444;")
        root.addWidget(self.lbl_footer)

        self.setCentralWidget(central)

    def _build_legend(self) -> QHBoxLayout:
        lay = QHBoxLayout()
        lay.setSpacing(8)

        title = QLabel("Leyenda:")
        title.setStyleSheet("font-weight:600;")
        lay.addWidget(title)

        for code in ["M", "T", "L", "G"]:
            chip = QLabel(f"{code} = {TURN_LABEL[code]}")
            chip.setAlignment(Qt.AlignCenter)
            chip.setStyleSheet(
                f"""
                QLabel {{
                    background: {TURN_BG[code]};
                    color: {TURN_FG[code]};
                    border: 1px solid #cfcfcf;
                    border-radius: 10px;
                    padding: 4px 10px;
                    font-weight: 600;
                }}
                """
            )
            chip.setToolTip(TURN_HOURS[code])
            lay.addWidget(chip)

        lay.addStretch(1)
        return lay

    def _load_table(self) -> None:
        self.table.blockSignals(True)

        self.table.setRowCount(len(self._employees))
        base_font = QFont()
        base_font.setPointSize(11)

        for r, emp in enumerate(self._employees):
            name_item = QTableWidgetItem(f"{emp.code} - {emp.name}")
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            name_item.setFont(base_font)
            self.table.setItem(r, 0, name_item)

            week = self._schedule.get(emp.code, ["L"] * 7)
            for c, value in enumerate(week, start=1):
                v = (value or "L").strip().upper()
                it = QTableWidgetItem(v)
                it.setTextAlignment(Qt.AlignCenter)
                it.setFont(base_font)
                self._apply_turn_style(it, v)
                self.table.setItem(r, c, it)

        self.table.blockSignals(False)
        self._update_footer()

    def _apply_turn_style(self, item: QTableWidgetItem, value: str) -> None:
        v = (value or "").strip().upper()
        if v not in TURN_BG:
            item.setBackground(QColor("#FFFFFF"))
            item.setForeground(QColor("#000000"))
            item.setToolTip("")
            return

        item.setBackground(QColor(TURN_BG[v]))
        item.setForeground(QColor(TURN_FG[v]))
        item.setToolTip(f"{v} = {TURN_LABEL[v]}")

    def _compute_coverage(self) -> List[Coverage]:
        cover: List[Coverage] = []
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

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        # Solo aplica a columnas de días; la 0 es "Empleado"
        if item.column() == 0:
            return

        v = (item.text() or "").strip().upper()
        if not v:
            v = "L"
        item.setText(v)

        self._apply_turn_style(item, v)
        self._set_dirty(True)
        self._update_footer()

    def _on_save(self) -> None:
        if not self._dirty:
            self._toast("Nada que guardar (demo).")
            return
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
