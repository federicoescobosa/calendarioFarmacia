from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import List, Dict, Optional

from PySide6.QtCore import Qt, QDate, QTimer
from PySide6.QtGui import QFont, QColor, QGuiApplication
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDateEdit,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
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

# --- Paleta UI ---
ACCENT = "#1E88E5"
ACCENT_DARK = "#1565C0"
SURFACE_2 = "#F6F8FB"
TEXT = "#1F2937"
TEXT_MUTED = "#6B7280"
BORDER = "#E5E7EB"

# --------------------------
# Turnos
# --------------------------
TURN_DEFS: Dict[str, Dict[str, str]] = {
    "M1": {"label": "Mañana 08:30–14:30", "hours": "08:30–14:30", "bg": "#DDEBFF", "fg": "#1F4E79"},
    "M2": {"label": "Mañana 09:00–14:00", "hours": "09:00–14:00", "bg": "#DFF7FF", "fg": "#0B4F6C"},
    "M3": {"label": "Mañana 09:30–14:00", "hours": "09:30–14:00", "bg": "#E4FFF0", "fg": "#0C5A2A"},
    "M4": {"label": "Mañana 10:00–14:30", "hours": "10:00–14:30", "bg": "#E9E4FF", "fg": "#3B2A7A"},
    "M5": {"label": "Mañana 10:00–13:30", "hours": "10:00–13:30", "bg": "#FFF2CC", "fg": "#6B4E00"},
    "T": {"label": "Tarde 17:00–20:30", "hours": "17:00–20:30", "bg": "#FFE6CC", "fg": "#7A3E00"},
    "L": {"label": "Libre", "hours": "No trabaja", "bg": "#F2F2F2", "fg": "#444444"},
    "G": {"label": "Guardia", "hours": "Pendiente de concretar", "bg": "#FFD9E6", "fg": "#7A0036"},
}
TURN_ORDER = ["M1", "M2", "M3", "M4", "M5", "T", "L", "G"]

# --------------------------
# Ausencias / Permisos (XXV Convenio Oficinas de Farmacia 2022-2024 - Art. 26/27)
# --------------------------
ABSENCE_DEFS: Dict[str, Dict[str, str]] = {
    "VAC": {"label": "Vacaciones", "bg": "#E5E7EB", "fg": "#111827"},
    "AP": {"label": "Asuntos propios (máx 2 días/año)", "bg": "#D1FAE5", "fg": "#065F46"},
    "BAJ": {"label": "Baja médica", "bg": "#FEE2E2", "fg": "#991B1B"},
    "FAL3": {"label": "Fallecimiento familiar (3 días)", "bg": "#FCE7F3", "fg": "#9D174D"},
    "FAL5": {"label": "Fallecimiento familiar + desplazamiento (5 días)", "bg": "#FBCFE8", "fg": "#9D174D"},
    "ENF5": {"label": "Enfermedad grave/hospitalización (5 días)", "bg": "#E0E7FF", "fg": "#3730A3"},
    "ENF3": {"label": "Enfermedad grave 2º afinidad (3 días)", "bg": "#E0E7FF", "fg": "#3730A3"},
    "BOD1": {"label": "Boda hijos/hermanos/padres (1 día)", "bg": "#FEF3C7", "fg": "#92400E"},
    "BOD20": {"label": "Boda del personal (20 días)", "bg": "#FDE68A", "fg": "#92400E"},
    "PER24D": {"label": "Permiso 24 dic (tarde)", "bg": "#DBEAFE", "fg": "#1D4ED8"},
    "PER31D": {"label": "Permiso 31 dic (tarde)", "bg": "#DBEAFE", "fg": "#1D4ED8"},
    "PERSAB": {"label": "Permiso Sábado Santo (mañana)", "bg": "#DBEAFE", "fg": "#1D4ED8"},
    "PER": {"label": "Permiso retribuido (genérico)", "bg": "#EEF2FF", "fg": "#3730A3"},
}

ABSENCE_ORDER = ["VAC", "AP", "BAJ", "FAL3", "FAL5", "ENF5", "ENF3", "BOD1", "BOD20", "PER24D", "PER31D", "PERSAB", "PER"]

ABSENCE_RULES: Dict[str, Dict[str, object]] = {
    "VAC": {"max_days": None},
    "BAJ": {"max_days": None},
    "AP": {"max_per_year_days": 2, "max_days": 2},
    "FAL3": {"max_days": 3},
    "FAL5": {"max_days": 5},
    "ENF5": {"max_days": 5},
    "ENF3": {"max_days": 3},
    "BOD1": {"max_days": 1},
    "BOD20": {"max_days": 20},
    "PER24D": {"max_days": 1, "forced_part": "PM"},
    "PER31D": {"max_days": 1, "forced_part": "PM"},
    "PERSAB": {"max_days": 1, "forced_part": "AM"},
    "PER": {"max_days": None},
}


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
    return {
        "A": ["M1", "M1", "M1", "M1", "M1", "L", "L"],
        "B": ["M2", "M2", "M2", "M2", "M2", "L", "L"],
        "C": ["M3", "T", "M3", "T", "M3", "L", "L"],
        "D": ["M5", "T", "M5", "T", "M5", "T", "L"],
        "E": ["M4", "M4", "M4", "M4", "M4", "T", "L"],
        "X": ["T", "L", "T", "L", "T", "L", "L"],
    }


@dataclass
class Coverage:
    day: str
    tardes: int
    objetivo: int = 4


@dataclass
class Absence:
    employee_code: str
    type_code: str
    start: date
    end: date
    part: str  # "FULL" | "AM" | "PM"
    notes: str = ""


class TurnDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):  # type: ignore[override]
        if index.column() == 0:
            return None
        combo = QComboBox(parent)
        combo.addItems(TURN_ORDER)
        combo.setEditable(False)
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
        self.resize(1400, 760)

        self._dirty = False
        self._employees: List[Employee] = get_demo_employees()
        self._schedule = get_demo_week_schedule()

        # Semana: ahora la controlamos con un datepicker en toolbar (Ir a)
        self._week_start: date = date(2026, 1, 1)  # demo inicial

        # Ausencias en memoria (luego persistimos)
        self._absences: List[Absence] = []

        # Toolbar
        self._toolbar = QToolBar("Semana")
        self.addToolBar(self._toolbar)

        self.btn_prev = QPushButton("‹ Semana")
        self.btn_today = QPushButton("Hoy")
        self.btn_next = QPushButton("Semana ›")

        self.lbl_week = QLabel("")
        self.lbl_week.setAlignment(Qt.AlignCenter)

        self.lbl_goto = QLabel("Ir a:")
        self.week_picker = QDateEdit()
        self.week_picker.setCalendarPopup(True)
        self.week_picker.setDisplayFormat("dd/MM/yyyy")
        self.week_picker.setDate(QDate(self._week_start.year, self._week_start.month, self._week_start.day))
        self.week_picker.dateChanged.connect(self._on_week_picker_changed)

        self._toolbar.addWidget(self.btn_prev)
        self._toolbar.addWidget(self.btn_today)
        self._toolbar.addWidget(self.btn_next)
        self._toolbar.addSeparator()
        self._toolbar.addWidget(self.lbl_goto)
        self._toolbar.addWidget(self.week_picker)
        self._toolbar.addSeparator()
        self._toolbar.addWidget(self.lbl_week)

        self.btn_prev.clicked.connect(self._prev_week)
        self.btn_today.clicked.connect(self._go_today)
        self.btn_next.clicked.connect(self._next_week)

        self._build_ui()
        self._refresh_week_header()
        self._load_table()

        # Extra: si alguien usa win.show() en vez de main.py, esto aún asegura centrar+ampliar
        QTimer.singleShot(0, self._maximize_on_current_screen)

    # --------------------------
    # Helpers de ventana / diálogos
    # --------------------------
    def _maximize_on_current_screen(self) -> None:
        # Garantiza que cae en una pantalla válida y maximiza.
        # Si la ventana estuviera fuera de pantalla por una config previa, la reubicamos al centro primero.
        scr = self.screen() or QGuiApplication.primaryScreen()
        if scr:
            geo = scr.availableGeometry()
            # Coloca la ventana en el centro antes de maximizar (evita "medio fuera")
            self.move(geo.center() - self.rect().center())
        self.showMaximized()
        self.activateWindow()
        self.raise_()

    def _center_on_parent(self, w: QWidget) -> None:
        parent = self if self.isVisible() else None
        if parent is not None:
            p = parent.frameGeometry()
            w.adjustSize()
            w.move(p.center() - w.rect().center())
            return

        scr = QGuiApplication.primaryScreen()
        if scr is None:
            return
        geo = scr.availableGeometry()
        w.adjustSize()
        w.move(geo.center() - w.rect().center())

    def _msg_info(self, title: str, text: str) -> None:
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Information)
        box.setWindowTitle(title)
        box.setText(text)
        box.setStandardButtons(QMessageBox.Ok)
        self._center_on_parent(box)
        box.exec()

    def _msg_warn(self, title: str, text: str) -> None:
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Warning)
        box.setWindowTitle(title)
        box.setText(text)
        box.setStandardButtons(QMessageBox.Ok)
        self._center_on_parent(box)
        box.exec()

    def _msg_question(self, title: str, text: str) -> bool:
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Question)
        box.setWindowTitle(title)
        box.setText(text)
        box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        box.setDefaultButton(QMessageBox.No)
        self._center_on_parent(box)
        res = box.exec()
        return res == QMessageBox.Yes

    # --------------------------
    # UI
    # --------------------------
    def _build_ui(self) -> None:
        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        sidebar_container = QWidget()
        sidebar_container.setFixedWidth(270)
        sidebar_layout = QVBoxLayout(sidebar_container)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(10)

        header = QLabel("Menú")
        header.setStyleSheet(
            f"""
            QLabel {{
                color: {TEXT};
                font-size: 14px;
                font-weight: 700;
                padding: 10px 12px 0px 12px;
            }}
            """
        )
        sub = QLabel("Farmacia")
        sub.setStyleSheet(
            f"""
            QLabel {{
                color: {TEXT_MUTED};
                font-size: 12px;
                padding: 0px 12px 6px 12px;
            }}
            """
        )

        self.sidebar = QListWidget()
        self.sidebar.setSpacing(6)
        self.sidebar.setStyleSheet(
            f"""
            QListWidget {{
                border: 1px solid {BORDER};
                border-radius: 14px;
                background: {SURFACE_2};
                padding: 10px;
                font-size: 13px;
                outline: 0;
            }}

            QListWidget::item {{
                color: {TEXT};
                background: transparent;
                padding: 12px 12px;
                border-radius: 12px;
            }}

            QListWidget::item:hover {{
                background: #EAF2FF;
            }}

            QListWidget::item:selected {{
                background: {ACCENT};
                color: #FFFFFF;
                font-weight: 700;
                border-left: 4px solid {ACCENT_DARK};
                padding-left: 8px;
            }}
            """
        )

        sidebar_layout.addWidget(header)
        sidebar_layout.addWidget(sub)
        sidebar_layout.addWidget(self.sidebar, 1)

        # Solo calendario en este zip (mantengo tu estructura)
        root.addWidget(sidebar_container)

        # Página principal: calendario
        self._pages = QWidget()
        pages_lay = QVBoxLayout(self._pages)
        pages_lay.setContentsMargins(0, 0, 0, 0)
        pages_lay.setSpacing(10)

        header_row = QHBoxLayout()
        self.lbl_dirty = QLabel("● Cambios sin guardar")
        self.lbl_dirty.setStyleSheet("font-weight:600; color:#b00020;")
        self.lbl_dirty.setVisible(False)

        self.btn_save = QPushButton("Guardar")
        self.btn_save.clicked.connect(self._on_save)

        header_row.addWidget(self.lbl_dirty)
        header_row.addStretch(1)
        header_row.addWidget(self.btn_save)
        pages_lay.addLayout(header_row)

        pages_lay.addLayout(self._build_legend())

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

        self.table.setEditTriggers(QTableWidget.DoubleClicked | QTableWidget.SelectedClicked)
        self._turn_delegate = TurnDelegate(self.table)
        self.table.setItemDelegate(self._turn_delegate)

        self.table.itemChanged.connect(self._on_item_changed)
        pages_lay.addWidget(self.table)

        self.lbl_footer = QLabel("")
        self.lbl_footer.setAlignment(Qt.AlignLeft)
        self.lbl_footer.setStyleSheet("color:#444;")
        pages_lay.addWidget(self.lbl_footer)

        root.addWidget(self._pages, 1)
        self.setCentralWidget(central)

    def _build_legend(self) -> QHBoxLayout:
        lay = QHBoxLayout()
        lay.setSpacing(8)

        t1 = QLabel("Turnos:")
        t1.setStyleSheet("font-weight:600;")
        lay.addWidget(t1)

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

    # --------------------------
    # Semana / Fechas
    # --------------------------
    def _refresh_week_header(self) -> None:
        end = self._week_start + timedelta(days=6)
        self.lbl_week.setText(f"Semana ({self._week_start.strftime('%d/%m/%Y')} - {end.strftime('%d/%m/%Y')})")

        self.week_picker.blockSignals(True)
        self.week_picker.setDate(QDate(self._week_start.year, self._week_start.month, self._week_start.day))
        self.week_picker.blockSignals(False)

        headers = ["Empleado"]
        for i, d in enumerate(DAYS):
            day_date = self._week_start + timedelta(days=i)
            headers.append(f"{d}\n{day_date.strftime('%d/%m')}")
        self.table.setHorizontalHeaderLabels(headers)

    def _on_week_picker_changed(self, qd: QDate) -> None:
        self._week_start = self._qdate_to_date(qd)
        self._refresh_week_header()
        self._load_table()

    def _prev_week(self) -> None:
        self._week_start = self._week_start - timedelta(days=7)
        self._refresh_week_header()
        self._load_table()

    def _next_week(self) -> None:
        self._week_start = self._week_start + timedelta(days=7)
        self._refresh_week_header()
        self._load_table()

    def _go_today(self) -> None:
        self._week_start = date.today()
        self._refresh_week_header()
        self._load_table()

    @staticmethod
    def _qdate_to_date(qd: QDate) -> date:
        return date(qd.year(), qd.month(), qd.day())

    # --------------------------
    # Datos / Lógica
    # --------------------------
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
        item.setFlags(item.flags() | Qt.ItemIsEditable)

    def _compute_coverage(self) -> List[Coverage]:
        cover: List[Coverage] = []
        for day_idx, day in enumerate(DAYS, start=1):
            tardes = 0
            for r in range(self.table.rowCount()):
                it = self.table.item(r, day_idx)
                if it is None:
                    continue
                v = (it.text() or "").strip().upper()
                if v == "T":
                    tardes += 1
            cover.append(Coverage(day=day, tardes=tardes))
        return cover

    def _update_footer(self) -> None:
        cover = self._compute_coverage()
        chunks = [f"{c.day}: Tarde {c.tardes}/{c.objetivo}" for c in cover]
        self.lbl_footer.setText("Cobertura tardes:  " + "   |   ".join(chunks))

    def _set_dirty(self, dirty: bool) -> None:
        self._dirty = dirty
        self.lbl_dirty.setVisible(dirty)

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if item.column() == 0:
            return

        if not (item.flags() & Qt.ItemIsEditable):
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
            if not self._msg_question("Salir", "Hay cambios sin guardar (demo). ¿Salir igualmente?"):
                event.ignore()
                return
        event.accept()

    def _toast(self, msg: str) -> None:
        self._msg_info("Info", msg)

    # --------------------------
    # Validación (usos de QMessageBox centrados)
    # --------------------------
    def _warn_ausencias(self, msg: str) -> None:
        self._msg_warn("Ausencias", msg)
