from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import List, Dict, Optional

from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont, QColor
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
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from farmacia_app.ui.employees_page import EmployeesPage

# Pantalla de Reglas (diálogo) integrada desde el menú lateral.
# La pantalla en sí NO se toca; solo se abre desde navegación.
from farmacia_app.ui.rules_dialog import RulesDialog, default_ruleset

# >>> FESTIVOS (SQLite cache)
from farmacia_app.data.holidays_repository import HolidaysRepository

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
# Ausencias / Permisos
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

        # Reglas (por ahora en memoria). Todavía NO reemplazan la lógica hardcode del calendario.
        self._ruleset = default_ruleset(self._employees)

        # Para que al pulsar "Reglas" en el menú lateral volvamos a la sección anterior.
        self._last_non_rules_row: int = 0

        # Semana: ahora la controlamos con un datepicker en toolbar (Ir a)
        self._week_start: date = date(2026, 1, 1)  # demo inicial

        # Ausencias en memoria (luego persistimos)
        self._absences: List[Absence] = []

        # >>> FESTIVOS (España + Andalucía) - si no están en BD, los descarga y los guarda.
        self._holidays = HolidaysRepository()
        y = date.today().year
        self._holidays.ensure_year(country_code="ES", subdivision_code="ES-AN", year=y)
        self._holidays.ensure_year(country_code="ES", subdivision_code="ES-AN", year=y + 1)

        # Toolbar
        self._toolbar = QToolBar("Semana")
        self.addToolBar(self._toolbar)

        self.btn_prev = QPushButton("‹ Semana")
        self.btn_today = QPushButton("Hoy")
        self.btn_next = QPushButton("Semana ›")

        self.lbl_week = QLabel("")
        self.lbl_week.setAlignment(Qt.AlignCenter)

        # Nuevo: selector "Ir a"
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

    # --------------------------
    # UI / Navegación
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

        self._pages = QStackedWidget()
        self._pages.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._page_index: Dict[str, int] = {}

        self._add_page("Calendario", self._build_calendar_page())
        self._add_page("Empleados", EmployeesPage())
        self._add_page("Turnos", self._build_placeholder_page("Turnos", "Catálogo (M1..), colores y chips."))
        self._add_page("Reglas", self._build_placeholder_page("Reglas", "Coberturas, restricciones, preferencias."))
        self._add_page("Ausencias", self._build_absences_page())
        self._add_page("Validación", self._build_placeholder_page("Validación", "Alertas y conflictos accionables."))
        self._add_page("Exportar", self._build_placeholder_page("Exportar", "PDF / Excel / CSV / ICS."))
        self._add_page("Ajustes", self._build_placeholder_page("Ajustes", "Parámetros generales."))

        self.sidebar.currentRowChanged.connect(self._on_nav_changed)

        root.addWidget(sidebar_container)
        root.addWidget(self._pages, 1)

        self.setCentralWidget(central)
        self.sidebar.setCurrentRow(0)

    def _add_page(self, title: str, widget: QWidget) -> None:
        item = QListWidgetItem(title)
        item.setToolTip(title)
        self.sidebar.addItem(item)
        idx = self._pages.addWidget(widget)
        self._page_index[title] = idx

    def _on_nav_changed(self, row: int) -> None:
        if row < 0:
            return

        # "Reglas" debe abrir el diálogo sin romper el menú lateral ni perder páginas.
        if row == self._page_index.get("Reglas", -1):
            self._open_rules()

            # Volver a la última sección real (por defecto Calendario).
            self.sidebar.blockSignals(True)
            self.sidebar.setCurrentRow(self._last_non_rules_row)
            self.sidebar.blockSignals(False)
            return

        self._last_non_rules_row = row
        self._pages.setCurrentIndex(row)
        is_calendar = (row == self._page_index.get("Calendario", 0))
        self._toolbar.setVisible(is_calendar)

        # Al entrar en Ausencias: por UX, ponemos por defecto el inicio/fin al día actual del calendario
        if row == self._page_index.get("Ausencias", -1):
            self.abs_start.blockSignals(True)
            self.abs_end.blockSignals(True)
            self.abs_start.setDate(QDate(self._week_start.year, self._week_start.month, self._week_start.day))
            self.abs_end.setDate(QDate(self._week_start.year, self._week_start.month, self._week_start.day))
            self.abs_end.setMinimumDate(self.abs_start.date())
            self.abs_start.blockSignals(False)
            self.abs_end.blockSignals(False)

    def _open_rules(self) -> None:
        dlg = RulesDialog(self, employees=self._employees, ruleset=self._ruleset)
        dlg.exec()
        self._ruleset = dlg.ruleset()

    def _build_placeholder_page(self, title: str, subtitle: str) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(18, 18, 18, 18)
        lay.setSpacing(10)

        h1 = QLabel(title)
        h1.setStyleSheet("font-size: 22px; font-weight: 700;")
        p = QLabel(subtitle)
        p.setStyleSheet("color:#555; font-size: 13px;")
        p.setWordWrap(True)

        hint = QLabel("Pendiente de implementar.")
        hint.setStyleSheet("color:#888; font-style: italic;")

        lay.addWidget(h1)
        lay.addWidget(p)
        lay.addSpacing(8)
        lay.addWidget(hint)
        lay.addStretch(1)
        return w

    # --------------------------
    # Página Calendario
    # --------------------------
    def _build_calendar_page(self) -> QWidget:
        page = QWidget()
        root = QVBoxLayout(page)
        root.setContentsMargins(0, 0, 0, 0)
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

        self.table.setEditTriggers(QTableWidget.DoubleClicked | QTableWidget.SelectedClicked)
        self._turn_delegate = TurnDelegate(self.table)
        self.table.setItemDelegate(self._turn_delegate)

        self.table.itemChanged.connect(self._on_item_changed)
        root.addWidget(self.table)

        self.lbl_footer = QLabel("")
        self.lbl_footer.setAlignment(Qt.AlignLeft)
        self.lbl_footer.setStyleSheet("color:#444;")
        root.addWidget(self.lbl_footer)

        return page

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

        lay.addSpacing(14)

        t2 = QLabel("Ausencias:")
        t2.setStyleSheet("font-weight:600;")
        lay.addWidget(t2)

        for code in ABSENCE_ORDER:
            d = ABSENCE_DEFS[code]
            chip = QLabel(code)
            chip.setAlignment(Qt.AlignCenter)
            chip.setStyleSheet(
                f"""
                QLabel {{
                    background: {d['bg']};
                    color: {d['fg']};
                    border: 1px solid #cfcfcf;
                    border-radius: 10px;
                    padding: 4px 10px;
                    font-weight: 700;
                }}
                """
            )
            chip.setToolTip(d["label"])
            lay.addWidget(chip)

        lay.addStretch(1)
        return lay

    # --------------------------
    # Página Ausencias
    # --------------------------
    def _build_absences_page(self) -> QWidget:
        page = QWidget()
        root = QVBoxLayout(page)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        title = QLabel("Ausencias")
        title.setStyleSheet("font-size: 22px; font-weight: 700;")
        subtitle = QLabel(
            "Registra vacaciones, asuntos propios y permisos del convenio (incluye boda: 20 días personal, "
            "boda familiar 1 día, tardes 24/31 dic, sábado santo mañana)."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color:#555; font-size: 13px;")
        root.addWidget(title)
        root.addWidget(subtitle)

        form = QHBoxLayout()
        form.setSpacing(10)

        self.abs_emp = QComboBox()
        self.abs_emp.addItems([f"{e.code} - {e.name}" for e in self._employees])

        self.abs_type = QComboBox()
        self.abs_type.addItems([f"{c} - {ABSENCE_DEFS[c]['label']}" for c in ABSENCE_ORDER])
        self.abs_type.currentIndexChanged.connect(self._on_abs_type_changed)

        self.abs_start = QDateEdit()
        self.abs_start.setCalendarPopup(True)
        self.abs_start.setDisplayFormat("dd/MM/yyyy")
        self.abs_start.setDate(QDate(self._week_start.year, self._week_start.month, self._week_start.day))
        self.abs_start.dateChanged.connect(self._on_abs_start_changed)

        self.abs_end = QDateEdit()
        self.abs_end.setCalendarPopup(True)
        self.abs_end.setDisplayFormat("dd/MM/yyyy")
        self.abs_end.setDate(QDate(self._week_start.year, self._week_start.month, self._week_start.day))
        self.abs_end.setMinimumDate(self.abs_start.date())

        self.abs_part = QComboBox()
        self.abs_part.addItems(["Día completo", "Mañana", "Tarde"])

        self.abs_notes = QLineEdit()
        self.abs_notes.setPlaceholderText("Notas (opcional)")

        self.abs_add = QPushButton("Añadir")
        self.abs_add.clicked.connect(self._add_absence)

        form.addWidget(QLabel("Empleado"))
        form.addWidget(self.abs_emp, 1)
        form.addWidget(QLabel("Tipo"))
        form.addWidget(self.abs_type, 1)
        form.addWidget(QLabel("Inicio"))
        form.addWidget(self.abs_start)
        form.addWidget(QLabel("Fin"))
        form.addWidget(self.abs_end)
        form.addWidget(QLabel("Parte"))
        form.addWidget(self.abs_part)
        form.addWidget(self.abs_notes, 2)
        form.addWidget(self.abs_add)

        root.addLayout(form)

        self.abs_table = QTableWidget()
        self.abs_table.setColumnCount(6)
        self.abs_table.setHorizontalHeaderLabels(["Empleado", "Tipo", "Inicio", "Fin", "Parte", "Notas"])
        self.abs_table.verticalHeader().setVisible(False)
        self.abs_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.abs_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.abs_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.abs_table.setAlternatingRowColors(True)

        hh = self.abs_table.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.Stretch)

        root.addWidget(self.abs_table, 1)

        actions = QHBoxLayout()
        self.abs_delete = QPushButton("Borrar seleccionado")
        self.abs_delete.clicked.connect(self._delete_selected_absence)
        actions.addStretch(1)
        actions.addWidget(self.abs_delete)
        root.addLayout(actions)

        self._refresh_absences_table()
        return page

    def _on_abs_start_changed(self) -> None:
        self.abs_end.setMinimumDate(self.abs_start.date())
        if self.abs_end.date() < self.abs_start.date():
            self.abs_end.setDate(self.abs_start.date())
        self._on_abs_type_changed()

    def _on_abs_type_changed(self) -> None:
        code = self.abs_type.currentText().split(" - ", 1)[0].strip()
        rules = ABSENCE_RULES.get(code, {})

        forced_part = rules.get("forced_part")
        if forced_part == "PM":
            self.abs_part.setCurrentText("Tarde")
            self.abs_end.setDate(self.abs_start.date())
        elif forced_part == "AM":
            self.abs_part.setCurrentText("Mañana")
            self.abs_end.setDate(self.abs_start.date())

        max_days = rules.get("max_days")
        if isinstance(max_days, int) and max_days == 1:
            self.abs_end.setDate(self.abs_start.date())

    def _add_absence(self) -> None:
        emp_code = self.abs_emp.currentText().split(" - ", 1)[0].strip()
        type_code = self.abs_type.currentText().split(" - ", 1)[0].strip()

        start = self._qdate_to_date(self.abs_start.date())
        end = self._qdate_to_date(self.abs_end.date())
        if end < start:
            QMessageBox.warning(self, "Ausencias", "La fecha de fin no puede ser anterior a la de inicio.")
            return

        part_txt = self.abs_part.currentText()
        part = "FULL"
        if part_txt == "Mañana":
            part = "AM"
        elif part_txt == "Tarde":
            part = "PM"

        if part != "FULL" and start != end:
            QMessageBox.warning(self, "Ausencias", "Si eliges Mañana/Tarde debe ser un único día (inicio = fin).")
            return

        notes = self.abs_notes.text().strip()

        ok, reason = self._validate_absence(
            Absence(employee_code=emp_code, type_code=type_code, start=start, end=end, part=part, notes=notes)
        )
        if not ok:
            QMessageBox.warning(self, "Ausencias", reason)
            return

        self._absences.append(Absence(emp_code, type_code, start, end, part, notes))
        self.abs_notes.clear()

        self._refresh_absences_table()
        self._load_table()

    def _validate_absence(self, new_abs: Absence) -> tuple[bool, str]:
        code = new_abs.type_code
        rules = ABSENCE_RULES.get(code, {})

        forced_part = rules.get("forced_part")
        if forced_part and new_abs.part != forced_part:
            return False, f"Este tipo de permiso exige parte fija: {'Tarde' if forced_part=='PM' else 'Mañana'}."

        max_days = rules.get("max_days")
        days_len = (new_abs.end - new_abs.start).days + 1
        if isinstance(max_days, int) and days_len > max_days:
            return False, f"Este permiso no puede superar {max_days} día(s)."

        if code == "AP":
            if new_abs.start.year != new_abs.end.year:
                return False, "Asuntos propios debe estar dentro del mismo año."

            used = 0.0
            for a in self._absences:
                if a.employee_code != new_abs.employee_code or a.type_code != "AP":
                    continue
                if a.start.year != new_abs.start.year:
                    continue
                used += self._absence_units(a)

            used += self._absence_units(new_abs)

            max_per_year = rules.get("max_per_year_days", 2)
            if used > float(max_per_year) + 1e-9:
                return False, f"Asuntos propios: máximo {max_per_year} días/año. Ya llevas {used - self._absence_units(new_abs):g}."

            for day in self._iter_days(new_abs.start, new_abs.end):
                for a in self._absences:
                    if a.type_code != "AP":
                        continue
                    if a.employee_code == new_abs.employee_code:
                        continue
                    if a.start <= day <= a.end:
                        return False, f"Asuntos propios: ya hay otro empleado con AP el {day.strftime('%d/%m/%Y')}."

            for a in self._absences:
                if a.employee_code != new_abs.employee_code:
                    continue
                if a.type_code != "VAC":
                    continue
                if not (new_abs.end < a.start or new_abs.start > a.end):
                    return False, "Asuntos propios no puede solaparse con vacaciones."
                if (new_abs.end + timedelta(days=1)) == a.start or (new_abs.start - timedelta(days=1)) == a.end:
                    return False, "Asuntos propios no puede ir pegado a vacaciones (salvo acuerdo)."

            today = date.today()
            if new_abs.start < (today + timedelta(days=7)):
                return False, "Asuntos propios requiere solicitud con al menos 1 semana de antelación (salvo fuerza mayor)."

        if code == "BOD20":
            if days_len > 20:
                return False, "Boda del personal: máximo 20 días."

        if code == "BOD1" and days_len != 1:
            return False, "Boda de hijos/hermanos/padres: es 1 día (día de la boda)."

        if code in ("PER24D", "PER31D"):
            day = new_abs.start
            if new_abs.start != new_abs.end:
                return False, "Este permiso es de un único día."
            if code == "PER24D" and not (day.day == 24 and day.month == 12):
                return False, "Este permiso solo aplica el 24/12 (tarde)."
            if code == "PER31D" and not (day.day == 31 and day.month == 12):
                return False, "Este permiso solo aplica el 31/12 (tarde)."

        for a in self._absences:
            if (
                a.employee_code == new_abs.employee_code
                and a.type_code == new_abs.type_code
                and a.start == new_abs.start
                and a.end == new_abs.end
                and a.part == new_abs.part
            ):
                return False, "Esa ausencia ya existe."

        for a in self._absences:
            if a.employee_code != new_abs.employee_code:
                continue
            if not (new_abs.end < a.start or new_abs.start > a.end):
                return False, "No se permite solapar ausencias en el mismo empleado."

        return True, "OK"

    @staticmethod
    def _iter_days(start: date, end: date):
        d = start
        while d <= end:
            yield d
            d += timedelta(days=1)

    @staticmethod
    def _absence_units(a: Absence) -> float:
        days_len = (a.end - a.start).days + 1
        if a.part == "FULL":
            return float(days_len)
        return 0.5

    def _delete_selected_absence(self) -> None:
        row = self.abs_table.currentRow()
        if row < 0:
            return
        try:
            self._absences.pop(row)
        except IndexError:
            return
        self._refresh_absences_table()
        self._load_table()

    def _refresh_absences_table(self) -> None:
        self.abs_table.setRowCount(len(self._absences))
        base_font = QFont()
        base_font.setPointSize(11)

        emp_name_by_code = {e.code: e.name for e in self._employees}

        for r, a in enumerate(self._absences):
            emp = f"{a.employee_code} - {emp_name_by_code.get(a.employee_code, '')}"
            typ = f"{a.type_code} - {ABSENCE_DEFS.get(a.type_code, {}).get('label', a.type_code)}"
            ini = a.start.strftime("%d/%m/%Y")
            fin = a.end.strftime("%d/%m/%Y")
            parte = {"FULL": "Día completo", "AM": "Mañana", "PM": "Tarde"}.get(a.part, a.part)
            notes = a.notes

            for c, val in enumerate([emp, typ, ini, fin, parte, notes]):
                it = QTableWidgetItem(val)
                it.setFont(base_font)
                self.abs_table.setItem(r, c, it)

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
    # FESTIVOS (helpers)
    # --------------------------
    def _is_holiday(self, day: date) -> bool:
        return self._holidays.is_holiday(day=day, country_code="ES", subdivision_code="ES-AN")

    def _apply_holiday_style(self, item: QTableWidgetItem, day: date) -> None:
        name = self._holidays.holiday_name(day=day, country_code="ES", subdivision_code="ES-AN") or "Festivo"
        item.setBackground(QColor("#E6E6E6"))
        item.setForeground(QColor("#666666"))
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)

        prev = item.toolTip() or ""
        extra = f"Festivo: {name}"
        item.setToolTip((prev + "\n" if prev else "") + extra)

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

                cell_date = self._week_start + timedelta(days=(c - 1))
                abs_hit = self._find_absence(emp.code, cell_date)
                if abs_hit is not None:
                    self._apply_absence_style(it, abs_hit)

                # >>> FESTIVO: forzar 'L' + gris + no editable (prioridad final)
                if self._is_holiday(cell_date):
                    it.setText("L")
                    self._apply_turn_style(it, "L")  # asegura tooltip/estilo de Libre
                    self._apply_holiday_style(it, cell_date)

                self.table.setItem(r, c, it)

        self.table.blockSignals(False)
        self._update_footer()

    def _find_absence(self, emp_code: str, day: date) -> Optional[Absence]:
        for a in self._absences:
            if a.employee_code != emp_code:
                continue
            if a.start <= day <= a.end:
                return a
        return None

    def _apply_turn_style(self, item: QTableWidgetItem, code: str) -> None:
        v = (code or "").strip().upper()
        if v not in TURN_DEFS:
            v = "L"
        d = TURN_DEFS[v]

        item.setBackground(QColor(d["bg"]))
        item.setForeground(QColor(d["fg"]))
        item.setToolTip(f"{v} = {d['label']} · {d['hours']}")
        item.setFlags(item.flags() | Qt.ItemIsEditable)

    def _apply_absence_style(self, item: QTableWidgetItem, a: Absence) -> None:
        d = ABSENCE_DEFS.get(a.type_code, {"label": a.type_code, "bg": "#E5E7EB", "fg": "#111827"})
        part_txt = {"FULL": "Día completo", "AM": "Mañana", "PM": "Tarde"}.get(a.part, a.part)

        item.setText(a.type_code)
        item.setBackground(QColor(d["bg"]))
        item.setForeground(QColor(d["fg"]))
        tooltip = f"{a.type_code} · {d['label']} · {part_txt}"
        if a.notes:
            tooltip += f"\nNotas: {a.notes}"
        item.setToolTip(tooltip)

        item.setFlags(item.flags() & ~Qt.ItemIsEditable)

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

        # >>> Seguridad extra: si alguien intenta editar un festivo, lo bloqueamos y avisamos.
        cell_date = self._week_start + timedelta(days=(item.column() - 1))
        if self._is_holiday(cell_date):
            self.table.blockSignals(True)
            item.setText("L")
            self._apply_turn_style(item, "L")
            self._apply_holiday_style(item, cell_date)
            self.table.blockSignals(False)
            QMessageBox.information(self, "Festivo", "No se puede editar un día festivo.")
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
