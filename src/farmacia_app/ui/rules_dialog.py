from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from PySide6.QtCore import Qt, QDate
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from farmacia_app.ui.shared import TURN_DEFS, TURN_ORDER, Employee, get_demo_employees


class SaturdayPattern:
    NONE = "none"
    ALL = "all"
    ALTERNATE = "alternate"
    UNKNOWN = "unknown"

    LABELS = {
        NONE: "No trabaja sábados",
        ALL: "Todos los sábados",
        ALTERNATE: "Sábado sí / sábado no",
        UNKNOWN: "Por definir",
    }


@dataclass
class GlobalRules:
    target_afternoon_coverage_per_day: int = 4
    owner_free_afternoons_per_week: int = 2


@dataclass
class EmployeeRules:
    employee_code: str
    afternoons_per_week: int
    saturday_pattern: str
    allowed_turns: Set[str] = field(default_factory=set)
    special_guard_week: bool = False


@dataclass
class RuleOverride:
    employee_code: str
    start_date: QDate
    end_date: QDate
    afternoons_per_week: Optional[int] = None
    allowed_turns: Optional[Set[str]] = None
    saturday_pattern: Optional[str] = None
    note: str = ""


@dataclass
class RuleSet:
    global_rules: GlobalRules
    per_employee: Dict[str, EmployeeRules]
    overrides: List[RuleOverride]


def default_ruleset(employees: List[Employee]) -> RuleSet:
    per_employee: Dict[str, EmployeeRules] = {}
    all_turns = set(TURN_ORDER)

    for e in employees:
        per_employee[e.code] = EmployeeRules(
            employee_code=e.code,
            afternoons_per_week=0,
            saturday_pattern=SaturdayPattern.UNKNOWN,
            allowed_turns=set(all_turns),
            special_guard_week=False,
        )

    if "A" in per_employee:
        per_employee["A"].afternoons_per_week = 2
        per_employee["A"].saturday_pattern = SaturdayPattern.ALTERNATE

    if "B" in per_employee:
        per_employee["B"].afternoons_per_week = 2
        per_employee["B"].saturday_pattern = SaturdayPattern.UNKNOWN

    if "C" in per_employee:
        per_employee["C"].afternoons_per_week = 5
        per_employee["C"].saturday_pattern = SaturdayPattern.UNKNOWN

    if "D" in per_employee:
        per_employee["D"].afternoons_per_week = 5
        per_employee["D"].saturday_pattern = SaturdayPattern.ALL

    if "E" in per_employee:
        per_employee["E"].afternoons_per_week = 1
        per_employee["E"].saturday_pattern = SaturdayPattern.ALL
        per_employee["E"].special_guard_week = True

    if "X" in per_employee:
        per_employee["X"].afternoons_per_week = 3
        per_employee["X"].saturday_pattern = SaturdayPattern.UNKNOWN

    return RuleSet(
        global_rules=GlobalRules(target_afternoon_coverage_per_day=4, owner_free_afternoons_per_week=2),
        per_employee=per_employee,
        overrides=[],
    )


class AllowedTurnsDialog(QDialog):
    def __init__(self, parent: QWidget, initial: Set[str]):
        super().__init__(parent)
        self.setWindowTitle("Turnos permitidos")
        self.resize(420, 360)

        root = QVBoxLayout(self)

        info = QLabel("Marca qué códigos de turno están permitidos para este empleado.")
        info.setWordWrap(True)
        root.addWidget(info)

        self.list = QListWidget()
        self.list.setSelectionMode(QAbstractItemView.NoSelection)
        for code in TURN_ORDER:
            d = TURN_DEFS.get(code)
            text = code
            if d:
                text = f"{code}  —  {d['label']}"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, code)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if code in initial else Qt.Unchecked)
            self.list.addItem(item)
        root.addWidget(self.list, 1)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def selected_turns(self) -> Set[str]:
        out: Set[str] = set()
        for i in range(self.list.count()):
            item = self.list.item(i)
            if item.checkState() == Qt.Checked:
                out.add(str(item.data(Qt.UserRole)))
        return out


class OverrideEditorDialog(QDialog):
    def __init__(
        self,
        parent: QWidget,
        employees: List[Employee],
        base_turns: Set[str],
        existing: Optional[RuleOverride] = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Excepción temporal")
        self.resize(520, 300)

        self._employees = employees
        self._base_turns = set(base_turns)

        root = QVBoxLayout(self)
        form = QFormLayout()
        root.addLayout(form)

        self.cmb_emp = QComboBox()
        for e in employees:
            self.cmb_emp.addItem(f"{e.code} - {e.name}", e.code)
        form.addRow("Empleado", self.cmb_emp)

        self.dt_start = QDateEdit()
        self.dt_start.setCalendarPopup(True)
        self.dt_start.setDisplayFormat("dd/MM/yyyy")
        self.dt_end = QDateEdit()
        self.dt_end.setCalendarPopup(True)
        self.dt_end.setDisplayFormat("dd/MM/yyyy")

        today = QDate.currentDate()
        self.dt_start.setDate(today)
        self.dt_end.setDate(today.addDays(7))

        form.addRow("Inicio", self.dt_start)
        form.addRow("Fin", self.dt_end)

        self.chk_override_afternoons = QCheckBox("Sobrescribir tardes/semana")
        self.spin_afternoons = QSpinBox()
        self.spin_afternoons.setRange(0, 7)
        self.spin_afternoons.setValue(0)

        row1 = QHBoxLayout()
        row1.addWidget(self.chk_override_afternoons)
        row1.addStretch(1)
        row1.addWidget(QLabel("Valor:"))
        row1.addWidget(self.spin_afternoons)
        form.addRow("Tardes", row1)

        self.chk_override_turns = QCheckBox("Sobrescribir turnos permitidos")
        self.btn_turns = QPushButton("Editar…")
        self.lbl_turns = QLabel("")
        self._override_turns: Set[str] = set(base_turns)

        row2 = QHBoxLayout()
        row2.addWidget(self.chk_override_turns)
        row2.addWidget(self.btn_turns)
        row2.addWidget(self.lbl_turns, 1)
        form.addRow("Turnos", row2)

        self.chk_override_saturday = QCheckBox("Sobrescribir sábados")
        self.cmb_saturday = QComboBox()
        for k, v in SaturdayPattern.LABELS.items():
            self.cmb_saturday.addItem(v, k)

        row3 = QHBoxLayout()
        row3.addWidget(self.chk_override_saturday)
        row3.addStretch(1)
        row3.addWidget(self.cmb_saturday)
        form.addRow("Sábados", row3)

        self.note = QLabel("")
        self.note.setWordWrap(True)
        form.addRow("Nota", self.note)

        self.btn_turns.clicked.connect(self._edit_turns)
        self.chk_override_turns.toggled.connect(lambda _: self._refresh_turns_label())
        self._refresh_turns_label()

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        root.addWidget(btns)

        if existing:
            self._load_existing(existing)

    def _load_existing(self, ov: RuleOverride) -> None:
        idx = self.cmb_emp.findData(ov.employee_code)
        if idx >= 0:
            self.cmb_emp.setCurrentIndex(idx)
        self.dt_start.setDate(ov.start_date)
        self.dt_end.setDate(ov.end_date)

        if ov.afternoons_per_week is not None:
            self.chk_override_afternoons.setChecked(True)
            self.spin_afternoons.setValue(ov.afternoons_per_week)

        if ov.allowed_turns is not None:
            self.chk_override_turns.setChecked(True)
            self._override_turns = set(ov.allowed_turns)

        if ov.saturday_pattern is not None:
            self.chk_override_saturday.setChecked(True)
            idx = self.cmb_saturday.findData(ov.saturday_pattern)
            if idx >= 0:
                self.cmb_saturday.setCurrentIndex(idx)

        self._refresh_turns_label()

    def _edit_turns(self) -> None:
        dlg = AllowedTurnsDialog(self, self._override_turns)
        if dlg.exec() == QDialog.Accepted:
            self._override_turns = dlg.selected_turns()
            self._refresh_turns_label()

    def _refresh_turns_label(self) -> None:
        if not self.chk_override_turns.isChecked():
            self.lbl_turns.setText("(sin cambios)")
            self.btn_turns.setEnabled(False)
            return
        self.btn_turns.setEnabled(True)
        codes = [c for c in TURN_ORDER if c in self._override_turns]
        self.lbl_turns.setText(", ".join(codes) if codes else "(ninguno)")

    def _on_accept(self) -> None:
        if self.dt_end.date() < self.dt_start.date():
            QMessageBox.warning(self, "Fechas", "La fecha de fin no puede ser anterior a la de inicio.")
            return

        if self.chk_override_turns.isChecked() and not self._override_turns:
            QMessageBox.warning(self, "Turnos", "Si sobrescribes turnos permitidos, debes dejar al menos uno.")
            return

        self.accept()

    def build_override(self) -> RuleOverride:
        emp_code = str(self.cmb_emp.currentData())
        ov = RuleOverride(
            employee_code=emp_code,
            start_date=self.dt_start.date(),
            end_date=self.dt_end.date(),
        )

        if self.chk_override_afternoons.isChecked():
            ov.afternoons_per_week = int(self.spin_afternoons.value())

        if self.chk_override_turns.isChecked():
            ov.allowed_turns = set(self._override_turns)

        if self.chk_override_saturday.isChecked():
            ov.saturday_pattern = str(self.cmb_saturday.currentData())

        return ov


class RulesDialog(QDialog):
    def __init__(self, parent: QWidget, employees: Optional[List[Employee]] = None, ruleset: Optional[RuleSet] = None):
        super().__init__(parent)
        self.setWindowTitle("Reglas")
        self.resize(980, 640)

        self._employees = employees or get_demo_employees()
        self._ruleset = ruleset or default_ruleset(self._employees)
        self._dirty = False

        root = QVBoxLayout(self)

        self.tabs = QTabWidget()
        root.addWidget(self.tabs, 1)

        self.tab_base = QWidget()
        self.tab_overrides = QWidget()
        self.tabs.addTab(self.tab_base, "Reglas base")
        self.tabs.addTab(self.tab_overrides, "Excepciones")

        self._build_base_tab()
        self._build_overrides_tab()

        self.buttons = QDialogButtonBox(QDialogButtonBox.Close)
        self.buttons.rejected.connect(self._on_close)
        self.buttons.accepted.connect(self._on_close)
        root.addWidget(self.buttons)

        self._refresh_all()

    def ruleset(self) -> RuleSet:
        return self._ruleset

    def _build_base_tab(self) -> None:
        root = QVBoxLayout(self.tab_base)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        grp_global = QGroupBox("Reglas globales")
        gl = QFormLayout(grp_global)
        self.spin_target_afternoons = QSpinBox()
        self.spin_target_afternoons.setRange(1, 10)
        self.spin_owner_free = QSpinBox()
        self.spin_owner_free.setRange(0, 7)
        gl.addRow("Objetivo de cobertura por tarde (personas/día)", self.spin_target_afternoons)
        gl.addRow("Dueño: tardes libres por semana (objetivo)", self.spin_owner_free)
        root.addWidget(grp_global)

        btn_row = QHBoxLayout()
        self.btn_reset = QPushButton("Restablecer reglas base")
        self.btn_reset.clicked.connect(self._reset_base_rules)
        btn_row.addWidget(self.btn_reset)
        btn_row.addStretch(1)
        self.lbl_dirty = QLabel("● Cambios sin guardar")
        self.lbl_dirty.setStyleSheet("font-weight:600; color:#b00020;")
        self.lbl_dirty.setVisible(False)
        btn_row.addWidget(self.lbl_dirty)
        root.addLayout(btn_row)

        grp_emp = QGroupBox("Reglas por empleado")
        v = QVBoxLayout(grp_emp)
        v.setContentsMargins(8, 8, 8, 8)
        v.setSpacing(6)

        self.tbl_emp = QTableWidget()
        self.tbl_emp.setColumnCount(5)
        self.tbl_emp.setHorizontalHeaderLabels([
            "Empleado",
            "Tardes/semana",
            "Sábados",
            "Turnos permitidos",
            "Guardia (especial)",
        ])
        self.tbl_emp.verticalHeader().setVisible(False)
        self.tbl_emp.setSelectionMode(QAbstractItemView.NoSelection)
        self.tbl_emp.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl_emp.setAlternatingRowColors(True)
        self.tbl_emp.horizontalHeader().setStretchLastSection(True)
        v.addWidget(self.tbl_emp)
        root.addWidget(grp_emp, 1)

        self.spin_target_afternoons.valueChanged.connect(lambda _: self._mark_dirty())
        self.spin_owner_free.valueChanged.connect(lambda _: self._mark_dirty())

    def _populate_employee_table(self) -> None:
        self.tbl_emp.setRowCount(len(self._employees))
        for r, e in enumerate(self._employees):
            rules = self._ruleset.per_employee.get(e.code)
            if not rules:
                continue

            it = QTableWidgetItem(f"{e.code} - {e.name}")
            it.setFlags(it.flags() & ~Qt.ItemIsEditable)
            self.tbl_emp.setItem(r, 0, it)

            spin = QSpinBox()
            spin.setRange(0, 7)
            spin.setValue(int(rules.afternoons_per_week))
            spin.valueChanged.connect(lambda v, code=e.code: self._on_emp_afternoons_changed(code, int(v)))
            self.tbl_emp.setCellWidget(r, 1, spin)

            cmb = QComboBox()
            for k, lbl in SaturdayPattern.LABELS.items():
                cmb.addItem(lbl, k)
            idx = cmb.findData(rules.saturday_pattern)
            cmb.setCurrentIndex(idx if idx >= 0 else 0)
            cmb.currentIndexChanged.connect(
                lambda _i, code=e.code, c=cmb: self._on_emp_saturday_changed(code, str(c.currentData()))
            )
            self.tbl_emp.setCellWidget(r, 2, cmb)

            btn = QPushButton("Editar…")
            btn.clicked.connect(lambda _=False, code=e.code: self._edit_allowed_turns(code))
            summary = QLabel(self._allowed_turns_summary(rules.allowed_turns))
            summary.setTextInteractionFlags(Qt.TextSelectableByMouse)
            row = QHBoxLayout()
            w = QWidget()
            row.setContentsMargins(0, 0, 0, 0)
            row.addWidget(btn)
            row.addWidget(summary, 1)
            w.setLayout(row)
            self.tbl_emp.setCellWidget(r, 3, w)

            chk = QCheckBox("Sí")
            chk.setChecked(bool(rules.special_guard_week))
            chk.toggled.connect(lambda v, code=e.code: self._on_emp_guard_changed(code, bool(v)))
            self.tbl_emp.setCellWidget(r, 4, chk)

        self.tbl_emp.resizeColumnsToContents()

    def _allowed_turns_summary(self, turns: Set[str]) -> str:
        codes = [c for c in TURN_ORDER if c in turns]
        return ", ".join(codes) if codes else "(ninguno)"

    def _reset_base_rules(self) -> None:
        res = QMessageBox.question(
            self,
            "Restablecer",
            "Esto restablece las reglas base a los valores por defecto.\n"
            "Las excepciones NO se borran.\n\nContinuar?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if res != QMessageBox.Yes:
            return

        current_overrides = list(self._ruleset.overrides)
        self._ruleset = default_ruleset(self._employees)
        self._ruleset.overrides = current_overrides
        self._dirty = False
        self._refresh_all()

    def _on_emp_afternoons_changed(self, emp_code: str, value: int) -> None:
        self._ruleset.per_employee[emp_code].afternoons_per_week = int(value)
        self._mark_dirty()

    def _on_emp_saturday_changed(self, emp_code: str, pattern: str) -> None:
        self._ruleset.per_employee[emp_code].saturday_pattern = pattern
        self._mark_dirty()

    def _on_emp_guard_changed(self, emp_code: str, checked: bool) -> None:
        self._ruleset.per_employee[emp_code].special_guard_week = bool(checked)
        self._mark_dirty()

    def _edit_allowed_turns(self, emp_code: str) -> None:
        rules = self._ruleset.per_employee[emp_code]
        dlg = AllowedTurnsDialog(self, rules.allowed_turns)
        if dlg.exec() == QDialog.Accepted:
            sel = dlg.selected_turns()
            if not sel:
                QMessageBox.warning(self, "Turnos", "Debes permitir al menos un turno.")
                return
            rules.allowed_turns = set(sel)
            self._mark_dirty()
            self._refresh_base_tab_only()

    def _build_overrides_tab(self) -> None:
        root = QVBoxLayout(self.tab_overrides)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        top = QHBoxLayout()
        self.btn_add_ov = QPushButton("Añadir excepción")
        self.btn_edit_ov = QPushButton("Editar")
        self.btn_del_ov = QPushButton("Eliminar")
        top.addWidget(self.btn_add_ov)
        top.addWidget(self.btn_edit_ov)
        top.addWidget(self.btn_del_ov)
        top.addStretch(1)
        root.addLayout(top)

        self.tbl_ov = QTableWidget()
        self.tbl_ov.setColumnCount(6)
        self.tbl_ov.setHorizontalHeaderLabels([
            "Empleado",
            "Inicio",
            "Fin",
            "Tardes/sem (override)",
            "Turnos (override)",
            "Sábados (override)",
        ])
        self.tbl_ov.verticalHeader().setVisible(False)
        self.tbl_ov.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_ov.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tbl_ov.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl_ov.setAlternatingRowColors(True)
        self.tbl_ov.horizontalHeader().setStretchLastSection(True)
        root.addWidget(self.tbl_ov, 1)

        self.btn_add_ov.clicked.connect(self._add_override)
        self.btn_edit_ov.clicked.connect(self._edit_override)
        self.btn_del_ov.clicked.connect(self._delete_override)

    def _populate_overrides_table(self) -> None:
        self.tbl_ov.setRowCount(len(self._ruleset.overrides))

        emp_name = {e.code: e.name for e in self._employees}

        for r, ov in enumerate(self._ruleset.overrides):
            self.tbl_ov.setItem(r, 0, QTableWidgetItem(f"{ov.employee_code} - {emp_name.get(ov.employee_code, '')}"))
            self.tbl_ov.setItem(r, 1, QTableWidgetItem(ov.start_date.toString("dd/MM/yyyy")))
            self.tbl_ov.setItem(r, 2, QTableWidgetItem(ov.end_date.toString("dd/MM/yyyy")))
            self.tbl_ov.setItem(r, 3, QTableWidgetItem("" if ov.afternoons_per_week is None else str(ov.afternoons_per_week)))
            if ov.allowed_turns is None:
                self.tbl_ov.setItem(r, 4, QTableWidgetItem(""))
            else:
                self.tbl_ov.setItem(r, 4, QTableWidgetItem(self._allowed_turns_summary(ov.allowed_turns)))
            if ov.saturday_pattern is None:
                self.tbl_ov.setItem(r, 5, QTableWidgetItem(""))
            else:
                self.tbl_ov.setItem(r, 5, QTableWidgetItem(SaturdayPattern.LABELS.get(ov.saturday_pattern, ov.saturday_pattern)))

        self.tbl_ov.resizeColumnsToContents()

    def _selected_override_index(self) -> Optional[int]:
        rows = self.tbl_ov.selectionModel().selectedRows()
        if not rows:
            return None
        return int(rows[0].row())

    def _add_override(self) -> None:
        dlg = OverrideEditorDialog(self, self._employees, set(TURN_ORDER))
        if dlg.exec() != QDialog.Accepted:
            return
        self._ruleset.overrides.append(dlg.build_override())
        self._mark_dirty()
        self._refresh_overrides_tab_only()

    def _edit_override(self) -> None:
        idx = self._selected_override_index()
        if idx is None:
            QMessageBox.information(self, "Info", "Selecciona una excepción para editar.")
            return
        current = self._ruleset.overrides[idx]
        dlg = OverrideEditorDialog(self, self._employees, set(TURN_ORDER), existing=current)
        if dlg.exec() != QDialog.Accepted:
            return
        self._ruleset.overrides[idx] = dlg.build_override()
        self._mark_dirty()
        self._refresh_overrides_tab_only()

    def _delete_override(self) -> None:
        idx = self._selected_override_index()
        if idx is None:
            QMessageBox.information(self, "Info", "Selecciona una excepción para eliminar.")
            return
        res = QMessageBox.question(self, "Eliminar", "¿Eliminar esta excepción?", QMessageBox.Yes | QMessageBox.No)
        if res != QMessageBox.Yes:
            return
        self._ruleset.overrides.pop(idx)
        self._mark_dirty()
        self._refresh_overrides_tab_only()

    def _refresh_all(self) -> None:
        self._refresh_base_tab_only()
        self._refresh_overrides_tab_only()

    def _refresh_base_tab_only(self) -> None:
        self.spin_target_afternoons.blockSignals(True)
        self.spin_owner_free.blockSignals(True)
        self.spin_target_afternoons.setValue(int(self._ruleset.global_rules.target_afternoon_coverage_per_day))
        self.spin_owner_free.setValue(int(self._ruleset.global_rules.owner_free_afternoons_per_week))
        self.spin_target_afternoons.blockSignals(False)
        self.spin_owner_free.blockSignals(False)

        self.tbl_emp.blockSignals(True)
        self.tbl_emp.clearContents()
        self._populate_employee_table()
        self.tbl_emp.blockSignals(False)

        self.lbl_dirty.setVisible(self._dirty)

    def _refresh_overrides_tab_only(self) -> None:
        self.tbl_ov.blockSignals(True)
        self.tbl_ov.clearContents()
        self._populate_overrides_table()
        self.tbl_ov.blockSignals(False)

    def _mark_dirty(self) -> None:
        self._dirty = True
        self.lbl_dirty.setVisible(True)
        self._ruleset.global_rules.target_afternoon_coverage_per_day = int(self.spin_target_afternoons.value())
        self._ruleset.global_rules.owner_free_afternoons_per_week = int(self.spin_owner_free.value())

    def _on_close(self) -> None:
        self.accept()
