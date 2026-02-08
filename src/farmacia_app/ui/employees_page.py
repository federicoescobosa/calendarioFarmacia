from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from farmacia_app.data.employee_repository import EmployeeRepository, EmployeeRow


@dataclass
class EmployeeFormData:
    nombre: str
    apellido1: str
    apellido2: str
    dni: str


class EmployeeFormDialog(QDialog):
    def __init__(self, parent: QWidget, title: str, initial: Optional[EmployeeFormData] = None, dni_readonly: bool = False):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(520, 240)

        root = QVBoxLayout(self)

        form = QFormLayout()
        root.addLayout(form)

        self.in_nombre = QLineEdit()
        self.in_ap1 = QLineEdit()
        self.in_ap2 = QLineEdit()
        self.in_dni = QLineEdit()

        self.in_dni.setPlaceholderText("Ej: 12345678Z")
        self.in_dni.setReadOnly(dni_readonly)

        form.addRow("Nombre", self.in_nombre)
        form.addRow("Apellido 1", self.in_ap1)
        form.addRow("Apellido 2", self.in_ap2)
        form.addRow("DNI", self.in_dni)

        if initial:
            self.in_nombre.setText(initial.nombre)
            self.in_ap1.setText(initial.apellido1)
            self.in_ap2.setText(initial.apellido2)
            self.in_dni.setText(initial.dni)

        self.msg = QLabel("")
        self.msg.setStyleSheet("color:#b00020; font-weight:600;")
        self.msg.setWordWrap(True)
        root.addWidget(self.msg)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._validate)
        btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def _validate(self) -> None:
        nombre = self.in_nombre.text().strip()
        ap1 = self.in_ap1.text().strip()
        ap2 = self.in_ap2.text().strip()
        dni = self.in_dni.text().strip().upper()

        if not nombre or not ap1:
            self.msg.setText("Nombre y Apellido 1 son obligatorios.")
            return
        if not dni:
            self.msg.setText("El DNI es obligatorio.")
            return

        self.accept()

    def data(self) -> EmployeeFormData:
        return EmployeeFormData(
            nombre=self.in_nombre.text().strip(),
            apellido1=self.in_ap1.text().strip(),
            apellido2=self.in_ap2.text().strip(),
            dni=self.in_dni.text().strip().upper(),
        )


class EmployeesPage(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._repo = EmployeeRepository()

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(10)

        h1 = QLabel("Empleados")
        h1.setStyleSheet("font-size: 22px; font-weight: 700;")
        sub = QLabel("Alta, edición y baja. Incluye el Dueño.")
        sub.setStyleSheet("color:#555; font-size: 13px;")
        sub.setWordWrap(True)

        top = QHBoxLayout()
        self.btn_new = QPushButton("Nuevo empleado")
        self.btn_new.clicked.connect(self._new_employee)
        top.addWidget(self.btn_new)
        top.addStretch(1)

        root.addWidget(h1)
        root.addWidget(sub)
        root.addLayout(top)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Nombre completo", "DNI", "Tipo", "Acciones", ""])
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        root.addWidget(self.table, 1)

        self._reload()

    def _reload(self) -> None:
        employees = self._repo.list_all()

        self.table.setRowCount(len(employees))
        self.table.setColumnHidden(4, True)  # guardamos el id aquí

        for r, e in enumerate(employees):
            it_name = QTableWidgetItem(e.full_name if e.full_name.strip() else e.nombre)
            it_dni = QTableWidgetItem(e.dni)
            it_type = QTableWidgetItem("Dueño" if e.is_owner else "Empleado")

            it_name.setData(Qt.UserRole, e.id)

            self.table.setItem(r, 0, it_name)
            self.table.setItem(r, 1, it_dni)
            self.table.setItem(r, 2, it_type)

            # Acciones
            btn_detail = QPushButton("Detalle")
            btn_edit = QPushButton("Editar")
            btn_del = QPushButton("Borrar")

            btn_detail.clicked.connect(lambda _=False, emp_id=e.id: self._detail(emp_id))
            btn_edit.clicked.connect(lambda _=False, emp_id=e.id: self._edit(emp_id))
            btn_del.clicked.connect(lambda _=False, emp_id=e.id: self._delete(emp_id))

            if e.is_owner:
                btn_del.setEnabled(False)

            actions = QHBoxLayout()
            actions.setContentsMargins(0, 0, 0, 0)
            w = QWidget()
            actions.addWidget(btn_detail)
            actions.addWidget(btn_edit)
            actions.addWidget(btn_del)
            actions.addStretch(1)
            w.setLayout(actions)
            self.table.setCellWidget(r, 3, w)

            # id oculto
            self.table.setItem(r, 4, QTableWidgetItem(str(e.id)))

        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setStretchLastSection(True)

    def _new_employee(self) -> None:
        dlg = EmployeeFormDialog(self, "Crear empleado")
        if dlg.exec() != QDialog.Accepted:
            return

        d = dlg.data()
        try:
            self._repo.create(d.nombre, d.apellido1, d.apellido2, d.dni)
        except ValueError as ex:
            QMessageBox.warning(self, "Error", str(ex))
            return

        self._reload()

    def _detail(self, emp_id: int) -> None:
        # Placeholder: se definirá más adelante
        emp = self._repo.get_by_id(emp_id)
        if not emp:
            return
        QMessageBox.information(self, "Detalle", f"Pendiente.\n\n{emp.full_name}\nDNI: {emp.dni}")

    def _edit(self, emp_id: int) -> None:
        emp = self._repo.get_by_id(emp_id)
        if not emp:
            QMessageBox.warning(self, "Error", "Empleado no encontrado.")
            return

        initial = EmployeeFormData(
            nombre=emp.nombre,
            apellido1=emp.apellido1,
            apellido2=emp.apellido2,
            dni=emp.dni,
        )
        dlg = EmployeeFormDialog(self, "Editar empleado", initial=initial, dni_readonly=emp.is_owner)
        if dlg.exec() != QDialog.Accepted:
            return

        d = dlg.data()
        try:
            self._repo.update(emp_id, d.nombre, d.apellido1, d.apellido2, d.dni)
        except ValueError as ex:
            QMessageBox.warning(self, "Error", str(ex))
            return

        self._reload()

    def _delete(self, emp_id: int) -> None:
        emp = self._repo.get_by_id(emp_id)
        if not emp:
            return
        if emp.is_owner:
            QMessageBox.information(self, "Info", "No se puede borrar el dueño.")
            return

        res = QMessageBox.question(
            self,
            "Confirmación",
            f"¿Borrar al empleado?\n\n{emp.full_name}\nDNI: {emp.dni}",
            QMessageBox.Yes | QMessageBox.No,
        )
        if res != QMessageBox.Yes:
            return

        try:
            self._repo.delete(emp_id)
        except ValueError as ex:
            QMessageBox.warning(self, "Error", str(ex))
            return

        self._reload()
