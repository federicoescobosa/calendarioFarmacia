from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Dict, List

from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor, QFont, QPainter, QPageLayout, QPageSize
from PySide6.QtPrintSupport import QPrinter
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QStyledItemDelegate,
    QTableWidget,
    QTableWidgetItem,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from farmacia_app.data.employee_repository import EmployeeRepository, EmployeeRow
from farmacia_app.data.holidays_repository import HolidaysRepository
from farmacia_app.data.schedule_repository import ScheduleRepository
from farmacia_app.data.weekly_template_repository import WeeklyTemplateRepository
from farmacia_app.ui.employees_page import EmployeesPage
from farmacia_app.ui.rules_dialog import RulesDialog
from farmacia_app.ui.shared import DAYS, TURN_DEFS, TURN_ORDER

# --- Paleta UI ---
ACCENT = "#1E88E5"
ACCENT_DARK = "#1565C0"
SURFACE_2 = "#F6F8FB"
TEXT = "#1F2937"
TEXT_MUTED = "#6B7280"
BORDER = "#E5E7EB"

# Festivos (OpenHolidays API)
HOL_COUNTRY = "ES"
HOL_SUBDIVISION = "ES-AN"  # Andalucía


def _app_version() -> str:
    try:
        from importlib.metadata import version  # py3.10+

        return version("calendario-farmacia")
    except Exception:
        return "0.1.0"


@dataclass
class EmployeeVM:
    id: int
    name: str


class TurnDelegate(QStyledItemDelegate):
    """Editor de celda: combo con TODOS los turnos."""

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
        if value not in TURN_ORDER:
            value = "L"
        editor.setCurrentText(value)

    def setModelData(self, editor, model, index):  # type: ignore[override]
        if editor is None:
            return
        model.setData(index, editor.currentText(), Qt.EditRole)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        # TODOS los botones en rojo (global)
        self.setStyleSheet(
            """
            QPushButton {
                background-color: #C62828;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 8px 14px;
                font-weight: 700;
            }
            QPushButton:hover { background-color: #B71C1C; }
            QPushButton:pressed { background-color: #8E0000; }
            QPushButton:disabled { background-color: #E0E0E0; color: #9E9E9E; }
            """
        )

        self.setWindowTitle("Farmacia - Calendario semanal")
        self.resize(1400, 760)

        # Repos
        self._employees_repo = EmployeeRepository()
        self._template_repo = WeeklyTemplateRepository()
        self._schedule_repo = ScheduleRepository()
        self._holidays_repo = HolidaysRepository()

        # Estado UI/datos
        self._dirty: bool = False
        self._week_start: date = date.today()
        self._employees: List[EmployeeVM] = []
        # turns visibles en la tabla: {employee_id: [L..D]}
        self._week_turns: Dict[int, List[str]] = {}

        # Para que al pulsar "Reglas" volvamos a la sección anterior
        self._last_non_rules_row: int = 0

        # Toolbar semana (solo visible en página Calendario)
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

        # StatusBar: versión abajo a la derecha
        self._version_label = QLabel(f"v{_app_version()}")
        self._version_label.setStyleSheet("color:#6B7280; padding-right:8px;")
        self.statusBar().addPermanentWidget(self._version_label)

        self._build_ui()
        self._sync_from_db()
        self._refresh_week_header()
        self._load_table()

    # --------------------------
    # Sync DB -> memoria
    # --------------------------
    def _sync_from_db(self) -> None:
        rows: List[EmployeeRow] = self._employees_repo.list_all()
        # compat: algunos repos tienen full_name, otros nombre
        self._employees = [EmployeeVM(id=r.id, name=(r.full_name if getattr(r, "full_name", "").strip() else r.nombre)) for r in rows]
        self._rebuild_week_turns()

        if hasattr(self, "_employees_page") and isinstance(self._employees_page, EmployeesPage):
            self._employees_page.reload()

    def _rebuild_week_turns(self) -> None:
        emp_ids = [e.id for e in self._employees]
        template = self._template_repo.load_all(emp_ids)
        saved = self._schedule_repo.load_week(emp_ids, self._week_start)

        out: Dict[int, List[str]] = {}
        for eid in emp_ids:
            week = ["L"] * 7
            tpl = template.get(eid, ["L"] * 7)
            sav = saved.get(eid, [""] * 7)

            for i in range(7):
                code = (sav[i] or "").strip().upper()
                if code:
                    week[i] = code if code in TURN_ORDER else "L"
                else:
                    t = (tpl[i] or "L").strip().upper()
                    week[i] = t if t in TURN_ORDER else "L"

            out[eid] = week

        self._week_turns = out
        self._set_dirty(False)

    # --------------------------
    # UI / Navegación
    # --------------------------
    def _build_ui(self) -> None:
        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        # Sidebar
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

        # Pages
        self._pages = QStackedWidget()
        self._pages.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._page_index: Dict[str, int] = {}

        self._add_page("Calendario", self._build_calendar_page())

        self._employees_page = EmployeesPage()
        self._employees_page.employees_changed.connect(self._on_employees_changed)
        self._add_page("Empleados", self._employees_page)

        self._add_page("Turnos", self._build_placeholder_page("Turnos", "Catálogo (M1..), colores y chips."))
        self._add_page("Reglas", self._build_placeholder_page("Reglas", "Plantilla semanal por empleado."))
        self._add_page("Ausencias", self._build_placeholder_page("Ausencias", "Pendiente."))
        self._add_page("Validación", self._build_placeholder_page("Validación", "Alertas y conflictos accionables."))
        self._add_page("Exportar", self._build_export_page())
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

        # “Reglas” abre un diálogo, no cambia de página
        if row == self._page_index.get("Reglas", -1):
            self._open_rules()
            self.sidebar.blockSignals(True)
            self.sidebar.setCurrentRow(self._last_non_rules_row)
            self.sidebar.blockSignals(False)
            return

        self._last_non_rules_row = row
        self._pages.setCurrentIndex(row)

        is_calendar = (row == self._page_index.get("Calendario", 0))
        self._toolbar.setVisible(is_calendar)

    def _open_rules(self) -> None:
        dlg = RulesDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self._rebuild_week_turns()
            self._load_table()

    def _on_employees_changed(self) -> None:
        self._sync_from_db()
        self._refresh_week_header()
        self._load_table()

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
    # Página Exportar (PDF)
    # --------------------------
    def _build_export_page(self) -> QWidget:
        page = QWidget()
        root = QVBoxLayout(page)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        h1 = QLabel("Exportar")
        h1.setStyleSheet("font-size: 22px; font-weight: 700;")
        p = QLabel("Genera un PDF del calendario semanal para enviarlo e imprimirlo cuando quieras.")
        p.setStyleSheet("color:#555; font-size: 13px;")
        p.setWordWrap(True)

        self._export_info = QLabel("")
        self._export_info.setStyleSheet("color:#6B7280; font-size: 12px;")
        self._export_info.setWordWrap(True)

        self.btn_export_pdf = QPushButton("Exportar semana actual a PDF")
        self.btn_export_pdf.clicked.connect(self._on_export_pdf)

        root.addWidget(h1)
        root.addWidget(p)
        root.addSpacing(8)
        root.addWidget(self.btn_export_pdf)
        root.addWidget(self._export_info)
        root.addStretch(1)
        return page

    def _on_export_pdf(self) -> None:
        default_name = f"calendario_{self._week_start.strftime('%Y-%m-%d')}.pdf"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar calendario a PDF",
            default_name,
            "PDF (*.pdf)",
        )
        if not path:
            return
        if not path.lower().endswith(".pdf"):
            path = path + ".pdf"

        try:
            widget = self._build_pdf_widget()
            self._render_widget_to_pdf(widget, path)
            self._export_info.setText(f"PDF generado: {path}")
            QMessageBox.information(self, "Exportar", "PDF generado correctamente.")
        except Exception as e:
            QMessageBox.critical(self, "Exportar", f"No se pudo generar el PDF.\n\nDetalle: {e}")

    def _build_pdf_widget(self) -> QWidget:
        """
        Construye un widget SOLO para PDF, replicando estilo:
        - Título
        - Leyenda
        - Tabla con los mismos colores que el calendario
        """
        w = QWidget()
        w.setStyleSheet("background: white;")  # PDF fondo blanco

        root = QVBoxLayout(w)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(10)

        end = self._week_start + timedelta(days=6)
        title = QLabel(f"Calendario semanal ({self._week_start.strftime('%d/%m/%Y')} - {end.strftime('%d/%m/%Y')})")
        title.setStyleSheet("font-size: 18px; font-weight: 700;")
        root.addWidget(title)

        root.addLayout(self._build_legend())

        t = QTableWidget()
        t.setColumnCount(1 + len(DAYS))
        t.setRowCount(len(self._employees))
        t.verticalHeader().setVisible(False)
        t.setAlternatingRowColors(True)
        t.setShowGrid(True)
        t.setStyleSheet(
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
        h = t.horizontalHeader()
        h.setSectionResizeMode(QHeaderView.Stretch)
        h.setStretchLastSection(True)

        # Cabeceras igual que en pantalla (incluye “Festivo” si lo hay)
        for c in range(self.table.columnCount()):
            hi = self.table.horizontalHeaderItem(c)
            label = hi.text() if hi else ("Empleado" if c == 0 else DAYS[c - 1])
            new_hi = QTableWidgetItem(label)
            if hi and hi.toolTip():
                new_hi.setToolTip(hi.toolTip())
            t.setHorizontalHeaderItem(c, new_hi)

        base_font = QFont()
        base_font.setPointSize(11)

        for r, emp in enumerate(self._employees):
            name_item = QTableWidgetItem(emp.name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            name_item.setFont(base_font)
            t.setItem(r, 0, name_item)

            week = self._week_turns.get(emp.id, ["L"] * 7)
            for i in range(7):
                code = (week[i] or "L").strip().upper()
                if code not in TURN_DEFS:
                    code = "L"

                it = QTableWidgetItem(code)
                it.setTextAlignment(Qt.AlignCenter)
                it.setFont(base_font)
                it.setFlags(it.flags() & ~Qt.ItemIsEditable)

                # estilo turno + hint festivo (negrita)
                self._apply_turn_style(it, code)
                it.setFlags(it.flags() & ~Qt.ItemIsEditable)  # _apply_turn_style marca editable
                self._apply_holiday_hint_if_needed(item=it, column=i + 1)

                t.setItem(r, i + 1, it)

        t.resizeRowsToContents()
        root.addWidget(t)

        w.adjustSize()
        return w

    def _render_widget_to_pdf(self, widget: QWidget, output_path: str) -> None:
        """
        Genera PDF. QPrinter aquí se usa SOLO como backend de PDF.
        No imprime nada.
        """
        printer = QPrinter(QPrinter.HighResolution)
        printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setOutputFileName(output_path)

        # Qt6 (PySide6): setOrientation no existe -> setPageOrientation
        printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        printer.setPageOrientation(QPageLayout.Orientation.Landscape)

        painter = QPainter()
        if not painter.begin(printer):
            raise RuntimeError("No se pudo iniciar el motor de PDF (QPrinter).")

        # Compatibilidad: en tu PySide6 pageRect() pide argumento, evitamos pageRect().
        page = printer.pageLayout().paintRectPixels(printer.resolution())

        widget.resize(widget.sizeHint())
        w = max(widget.width(), 1)
        h = max(widget.height(), 1)

        x_scale = page.width() / w
        y_scale = page.height() / h
        scale = min(x_scale, y_scale)

        painter.save()
        painter.translate(page.x(), page.y())
        painter.scale(scale, scale)
        widget.render(painter)
        painter.restore()

        painter.end()

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

        # Leyenda
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

        lay.addStretch(1)
        return lay

    # --------------------------
    # Semana / Fechas
    # --------------------------
    def _refresh_week_header(self) -> None:
        # Asegura festivos (si hay internet, los cachea en BD)
        self._ensure_holidays_loaded_for_visible_week()

        end = self._week_start + timedelta(days=6)
        self.lbl_week.setText(f"Semana ({self._week_start.strftime('%d/%m/%Y')} - {end.strftime('%d/%m/%Y')})")

        self.week_picker.blockSignals(True)
        self.week_picker.setDate(QDate(self._week_start.year, self._week_start.month, self._week_start.day))
        self.week_picker.blockSignals(False)

        # Cabeceras con marcador de festivo
        self.table.setHorizontalHeaderItem(0, QTableWidgetItem("Empleado"))
        for i, d in enumerate(DAYS):
            day_date = self._week_start + timedelta(days=i)
            txt = f"{d}\n{day_date.strftime('%d/%m')}"
            name = self._holidays_repo.holiday_name(day=day_date, country_code=HOL_COUNTRY, subdivision_code=HOL_SUBDIVISION)
            if name:
                txt = f"{txt}\nFestivo"
            hi = QTableWidgetItem(txt)
            if name:
                hi.setToolTip(f"Festivo: {name}")
            self.table.setHorizontalHeaderItem(i + 1, hi)

    def _on_week_picker_changed(self, qd: QDate) -> None:
        self._week_start = self._qdate_to_date(qd)
        self._rebuild_week_turns()
        self._refresh_week_header()
        self._load_table()

    def _prev_week(self) -> None:
        self._week_start = self._week_start - timedelta(days=7)
        self._rebuild_week_turns()
        self._refresh_week_header()
        self._load_table()

    def _next_week(self) -> None:
        self._week_start = self._week_start + timedelta(days=7)
        self._rebuild_week_turns()
        self._refresh_week_header()
        self._load_table()

    def _go_today(self) -> None:
        self._week_start = date.today()
        self._rebuild_week_turns()
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
            name_item = QTableWidgetItem(emp.name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            name_item.setFont(base_font)
            self.table.setItem(r, 0, name_item)

            week = self._week_turns.get(emp.id, ["L"] * 7)
            for c, value in enumerate(week, start=1):
                v = (value or "L").strip().upper()
                if v not in TURN_DEFS:
                    v = "L"

                it = QTableWidgetItem(v)
                it.setTextAlignment(Qt.AlignCenter)
                it.setFont(base_font)
                self._apply_turn_style(it, v)
                self._apply_holiday_hint_if_needed(item=it, column=c)
                self.table.setItem(r, c, it)

        self.table.blockSignals(False)

    def _ensure_holidays_loaded_for_visible_week(self) -> None:
        years = {self._week_start.year, (self._week_start + timedelta(days=6)).year}
        for y in sorted(years):
            self._holidays_repo.ensure_year(country_code=HOL_COUNTRY, subdivision_code=HOL_SUBDIVISION, year=y)

    def _apply_holiday_hint_if_needed(self, *, item: QTableWidgetItem, column: int) -> None:
        day_date = self._week_start + timedelta(days=column - 1)
        name = self._holidays_repo.holiday_name(day=day_date, country_code=HOL_COUNTRY, subdivision_code=HOL_SUBDIVISION)
        if not name:
            return

        # Negrita + tooltip con festivo (sin tocar colores del turno)
        f = item.font()
        f.setBold(True)
        item.setFont(f)
        base_tip = item.toolTip() or ""
        extra = f"Festivo: {name}"
        item.setToolTip((base_tip + "\n\n" + extra).strip())

    def _apply_turn_style(self, item: QTableWidgetItem, code: str) -> None:
        v = (code or "").strip().upper()
        if v not in TURN_DEFS:
            v = "L"
        d = TURN_DEFS[v]

        item.setBackground(QColor(d["bg"]))
        item.setForeground(QColor(d["fg"]))
        item.setToolTip(f"{v} = {d['label']} · {d['hours']}")
        item.setFlags(item.flags() | Qt.ItemIsEditable)

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
        self._update_week_turns_from_table()
        self._set_dirty(True)

    def _update_week_turns_from_table(self) -> None:
        out: Dict[int, List[str]] = {}
        for r, emp in enumerate(self._employees):
            turns = []
            for c in range(1, 8):
                it = self.table.item(r, c)
                turns.append((it.text() if it else "L").strip().upper() or "L")
            out[emp.id] = turns
        self._week_turns = out

    def _on_save(self) -> None:
        if not self._dirty:
            QMessageBox.information(self, "Guardar", "No hay cambios que guardar.")
            return

        for emp in self._employees:
            turns = self._week_turns.get(emp.id, ["L"] * 7)
            self._schedule_repo.upsert_week(emp.id, self._week_start, turns)

        self._set_dirty(False)
        QMessageBox.information(self, "Guardar", "Semana guardada en la base de datos.")