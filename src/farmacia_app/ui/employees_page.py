from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
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
    email: str
    role: str


class EmployeeFormDialog(QDialog):
    def __init__(
        self,
        parent: QWidget,
        title: str,
        initial: Optional[EmployeeFormData] = None,
        dni_readonly: bool = False,
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(560, 320)

        root = QVBoxLayout(self)
        form = QFormLayout()
        root.addLayout(form)

        self.in_nombre = QLineEdit()
        self.in_ap1 = QLineEdit()
        self.in_ap2 = QLineEdit()
        self.in_dni = QLineEdit()
        self.in_email = QLineEdit()

        self.cb_role = QComboBox()
        self.cb_role.addItems(["Empleado", "Jefe"])

        self.in_dni.setReadOnly(dni_readonly)
        self.in_email.setPlaceholderText("correo@dominio.com")

        form.addRow("Nombre", self.in_nombre)
        form.addRow("Apellido 1", self.in_ap1)
        form.addRow("Apellido 2", self.in_ap2)
        form.addRow("DNI", self.in_dni)
        form.addRow("Correo electrónico", self.in_email)
        form.addRow("Rol", self.cb_role)

        if initial:
            self.in_nombre.setText(initial.nombre)
            self.in_ap1.setText(initial.apellido1)
            self.in_ap2.setText(initial.apellido2)
            self.in_dni.setText(initial.dni)
            self.in_email.setText(initial.email)
            self.cb_role.setCurrentText(initial.role if initial.role in ("Empleado", "Jefe") else "Empleado")

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
            email=self.in_email.text().strip(),
            role=self.cb_role.currentText().strip(),
        )


class EmployeesPage(QWidget):
    """
    Página del menú lateral: Empleados
    - Lista empleados
    - Alta/Edición/Borrado
    - Emite employees_changed cuando cambia algo (para refrescar calendario y reglas)
    """

    employees_changed = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._repo = EmployeeRepository()

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(10)

        title = QLabel("Empleados")
        title.setStyleSheet("font-size:22px; font-weight:700;")
        root.addWidget(title)

        top = QHBoxLayout()
        self.btn_add = QPushButton("Nuevo empleado")
        self.btn_add.clicked.connect(self._on_add)
        top.addWidget(self.btn_add)
        top.addStretch(1)
        root.addLayout(top)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["ID", "Nombre completo", "DNI", "Email", "Rol", "Acciones"])
        self.table.setColumnHidden(0, True)  # ocultamos ID
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        root.addWidget(self.table, 1)

        self._reload()

    # ✅ Método público (lo usa MainWindow)
    def reload(self) -> None:
        self._reload()

    def _reload(self) -> None:
        employees = self._repo.list_all()
        self.table.setRowCount(len(employees))

        for r, e in enumerate(employees):
            self.table.setItem(r, 0, QTableWidgetItem(str(e.id)))
            self.table.setItem(r, 1, QTableWidgetItem(e.full_name if e.full_name.strip() else e.nombre))
            self.table.setItem(r, 2, QTableWidgetItem(e.dni))
            self.table.setItem(r, 3, QTableWidgetItem(e.email))
            self.table.setItem(r, 4, QTableWidgetItem(e.role))

            btn_edit = QPushButton("Editar")
            btn_del = QPushButton("Borrar")
            btn_edit.clicked.connect(lambda _=False, emp_id=e.id: self._on_edit(emp_id))
            btn_del.clicked.connect(lambda _=False, emp_id=e.id: self._on_delete(emp_id))

            if e.is_owner:
                btn_del.setEnabled(False)

            w = QWidget()
            lay = QHBoxLayout(w)
            lay.setContentsMargins(0, 0, 0, 0)
            lay.addWidget(btn_edit)
            lay.addWidget(btn_del)
            lay.addStretch(1)
            self.table.setCellWidget(r, 5, w)

        self.table.resizeColumnsToContents()

    def _on_add(self) -> None:
        dlg = EmployeeFormDialog(self, "Crear empleado")
        if dlg.exec() != QDialog.Accepted:
            return

        d = dlg.data()
        try:
            self._repo.create(d.nombre, d.apellido1, d.apellido2, d.dni, d.email, d.role)
        except ValueError as ex:
            QMessageBox.warning(self, "Error", str(ex))
            return

        self._reload()
        self.employees_changed.emit()

    def _on_edit(self, emp_id: int) -> None:
        emp: Optional[EmployeeRow] = self._repo.get_by_id(emp_id)
        if not emp:
            QMessageBox.warning(self, "Error", "Empleado no encontrado.")
            return

        initial = EmployeeFormData(
            nombre=emp.nombre,
            apellido1=emp.apellido1,
            apellido2=emp.apellido2,
            dni=emp.dni,
            email=emp.email,
            role=emp.role,
        )

        dlg = EmployeeFormDialog(self, "Editar empleado", initial=initial, dni_readonly=emp.is_owner)
        if dlg.exec() != QDialog.Accepted:
            return

        d = dlg.data()
        try:
            self._repo.update(emp_id, d.nombre, d.apellido1, d.apellido2, d.dni, d.email, d.role)
        except ValueError as ex:
            QMessageBox.warning(self, "Error", str(ex))
            return

        self._reload()
        self.employees_changed.emit()

    def _on_delete(self, emp_id: int) -> None:
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
        self.employees_changed.emit()
