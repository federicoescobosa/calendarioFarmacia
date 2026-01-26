from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QStyledItemDelegate,
    QTableWidget,
    QTableWidgetItem,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

DAYS = ["L", "M", "X", "J", "V", "S", "D"]

# Definición única de turnos: etiqueta, horas, color fondo, color texto
TURN_DEFS: Dict[str, Dict[str, str]] = {
    # Mañanas escalonadas (intermedios)
    "M1": {"label": "Mañana 08:30–14:30", "hours": "08:30–14:30", "bg": "#DDEBFF", "fg": "#1F4E79"},
    "M2": {"label": "Mañana 09:00–14:00", "hours": "09:00–14:00", "bg": "#DFF7FF", "fg": "#0B4F6C"},
    "M3": {"label": "Mañana 09:30–14:00", "hours": "09:30–14:00", "bg": "#E4FFF0", "fg": "#0C5A2A"},
    "M4": {"label": "Mañana 10:00–14:30", "hours": "10:00–14:30", "bg": "#E9E4FF", "fg": "#3B2A7A"},
    "M5": {"label": "Mañana 10:00–13:30", "hours": "10:00–13:30", "bg": "#FFF2CC", "fg": "#6B4E00"},
    # Tarde
    "T": {"label": "Tarde 17:00–20:30", "hours": "17:00–20:30", "bg": "#FFE6CC", "fg": "#7A3E00"},
    # Libre / Guardia
    "L": {"label": "Libre", "hours": "No trabaja", "bg": "#F2F2F2", "fg": "#444444"},
    "G": {"label": "Guardia", "hours": "Pendiente de concretar", "bg": "#FFD9E6", "fg": "#7A0036"},
}

# Orden en dropdown y leyenda
TURN_ORDER = ["M1", "M2", "M3", "M4", "M5", "T", "L", "G"]


@dataclass
class Employee:
    code: str
    name: str


Schedule = dict[str, list[str]]  # employee_code -> 7 valores (L..D)


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
    # Demo: usamos los intermedios de mañana por persona (según vuestro patrón base)
    # Encarni: 08:30–14:30 -> M1
    # María : 09:00–14:00 -> M2
    # Fátima: 09:30–14:00 -> M3 (y tardes)
    # Belén : 10:00–13:30 -> M5 (y tardes + sábados)
    # Thalisa:10:00–14:30 -> M4 (y 1 tarde/semana cuando no guardia)
    return {
        "A": ["M1", "M1", "M1", "M1", "M1", "L", "L"],
        "B": ["M2", "M2", "M2", "M2", "M2", "L", "L"],
        "C": ["M3", "T",  "M3", "T",  "M3", "L", "L"],  # mezcla demo
        "D": ["M5", "T",  "M5", "T",  "M5", "T", "L"],
        "E": ["M4", "M4", "M4", "M4", "M4", "T", "L"],
        # Dueño demo (2 tardes libres)
        "X": ["T",  "L",  "T",  "L",  "T",  "L", "L"],
    }


@dataclass
class Coverage:
    day: str
    tardes: int
    objetivo: int = 4


class TurnDelegate(QStyledItemDelegate):
    """Delegate para editar celdas con un combo de turnos."""

    def createEditor(self, parent, option, index):  # type: ignore[override]
        if index.column() == 0:
            return None
        combo = QComboBox(parent)
        combo.addItems(TURN_ORDER)
        combo.setEditable(False)
        # Mostrar tooltip del item seleccionado al desplegar
        combo.setToolTip("Elige turno")
        return combo

    def setEditorData(self, editor, index):  # type: ignore[override]
        if editor is None:
            return
        value = (index.data() or "").strip().upper()
        if value not in TURN_DEFS:
            value = "L"
        editor.setCurrentText(value)

    def setModelData(self, editor, model, index):  # type: ignore[override]
        if editor is None:
            return
        model.setData(index, editor.currentText(), Qt.EditRole)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Farmacia - Calendario semanal (demo hardcode)")
        self.resize(1250, 720)

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

        root.addLayout(self._build_legend())

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

        self.table.setColumnWidth(0, 260)
        self.table.verticalHeader().setDefaultSectionSize(34)

        # Edición por click/doble click (combo). Sin tecleo libre.
        self.table.setEditTriggers(QTableWidget.DoubleClicked | QTableWidget.SelectedClicked)

        self._turn_delegate = TurnDelegate(self.table)
        self.table.setItemDelegate(self._turn_delegate)

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

        # Chips para todos los turnos
        for code in TURN_ORDER:
            d = TURN_DEFS[code]
            chip = QLabel(f"{code} = {d['label']}")
            chip.setAlignment(Qt.AlignCenter)
            chip.setStyleSheet(
                f"""
                QLabel {{
                    background: {d['bg']};
                    color: {d['fg']};
                    border: 1px solid #cfcfcf;
                    border-radius: 10px;
                    padding: 4px 10px;
                    font-weight: 600;
                }}
                """
            )
            chip.setToolTip(d["hours"])
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
                if v not in TURN_DEFS:
                    v = "L"

                it = QTableWidgetItem(v)
                it.setTextAlignment(Qt.AlignCenter)
                it.setFont(base_font)
                self._apply_turn_style(it, v)
                self.table.setItem(r, c, it)

        self.table.blockSignals(False)
        self._update_footer()

    def _apply_turn_style(self, item: QTableWidgetItem, code: str) -> None:
        v = (code or "").strip().upper()
        if v not in TURN_DEFS:
            v = "L"
        d = TURN_DEFS[v]

        item.setBackground(QColor(d["bg"]))
        item.setForeground(QColor(d["fg"]))
        item.setToolTip(f"{v} = {d['label']} · {d['hours']}")

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
        if item.column() == 0:
            return

        v = (item.text() or "").strip().upper()
        if v not in TURN_DEFS:
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
