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

DAYS = ["L", "M", "X", "J", "V", "S", "D"]

# --- Paleta (1 sitio) ---
ACCENT = "#1E88E5"        # azul principal
ACCENT_DARK = "#1565C0"   # azul oscuro para borde/indicador
SURFACE = "#FFFFFF"
SURFACE_2 = "#F6F8FB"     # fondo sidebar
TEXT = "#1F2937"          # gris oscuro
TEXT_MUTED = "#6B7280"    # gris medio
BORDER = "#E5E7EB"

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


class TurnDelegate(QStyledItemDelegate):
    """Delegate para editar celdas con un combo de turnos."""

    def createEditor(self, parent, option, index):  # type: ignore[override]
        if index.column() == 0:
            return None
        combo = QComboBox(parent)
        combo.addItems(TURN_ORDER)
        combo.setEditable(False)
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
    """Ventana principal con menú lateral + páginas."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Farmacia - Calendario semanal (demo hardcode)")
        self.resize(1400, 760)

        self._dirty = False
        self._employees: List[Employee] = get_demo_employees()
        self._schedule = get_demo_week_schedule()

        # Toolbar (solo útil para calendario; lo ocultamos en otras páginas)
        self._toolbar = QToolBar("Semana")
        self.addToolBar(self._toolbar)

        self.btn_prev = QPushButton("‹ Semana")
        self.btn_today = QPushButton("Semana actual")
        self.btn_next = QPushButton("Semana ›")
        self.lbl_week = QLabel("Semana demo (01/01/2026 - 07/01/2026)")
        self.lbl_week.setAlignment(Qt.AlignCenter)

        self._toolbar.addWidget(self.btn_prev)
        self._toolbar.addWidget(self.btn_today)
        self._toolbar.addWidget(self.btn_next)
        self._toolbar.addSeparator()
        self._toolbar.addWidget(self.lbl_week)

        self.btn_prev.clicked.connect(lambda: self._toast("Demo: navegación desactivada"))
        self.btn_today.clicked.connect(lambda: self._toast("Demo: navegación desactivada"))
        self.btn_next.clicked.connect(lambda: self._toast("Demo: navegación desactivada"))

        self._build_ui()
        self._load_table()

    # --------------------------
    # UI / Navegación
    # --------------------------
    def _build_ui(self) -> None:
        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        # --- Sidebar moderno (contenedor + título + lista) ---
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
                color: #FFFFFF;                 /* fuerza texto blanco visible */
                font-weight: 700;
                border-left: 4px solid {ACCENT_DARK};
                padding-left: 8px;              /* compensa el border-left */
            }}
            """
        )

        sidebar_layout.addWidget(header)
        sidebar_layout.addWidget(sub)
        sidebar_layout.addWidget(self.sidebar, 1)

        # --- Páginas ---
        self._pages = QStackedWidget()
        self._pages.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self._page_index: Dict[str, int] = {}

        self._add_page("Calendario", self._build_calendar_page())
        self._add_page("Empleados", self._build_placeholder_page("Empleados", "Alta/baja y horas objetivo."))
        self._add_page("Turnos", self._build_placeholder_page("Turnos", "Catálogo (M1..), colores y chips."))
        self._add_page("Reglas", self._build_placeholder_page("Reglas", "Coberturas, restricciones, preferencias."))
        self._add_page("Ausencias", self._build_placeholder_page("Ausencias", "Vacaciones, permisos, bajas."))
        self._add_page("Validación", self._build_placeholder_page("Validación", "Alertas y conflictos accionables."))
        self._add_page("Exportar", self._build_placeholder_page("Exportar", "PDF / Excel / CSV / ICS."))
        self._add_page("Ajustes", self._build_placeholder_page("Ajustes", "Parámetros generales."))
        self._add_page("Informes", self._build_placeholder_page("Informes", "Muestras históricos"))

        self.sidebar.currentRowChanged.connect(self._on_nav_changed)

        root.addWidget(sidebar_container)
        root.addWidget(self._pages, 1)

        self.setCentralWidget(central)

        # Página por defecto
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
        self._pages.setCurrentIndex(row)

        # Toolbar solo visible en calendario
        is_calendar = (row == self._page_index.get("Calendario", 0))
        self._toolbar.setVisible(is_calendar)

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

        title = QLabel("Leyenda:")
        title.setStyleSheet("font-weight:600;")
        lay.addWidget(title)

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
    # Datos / Lógica demo
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
