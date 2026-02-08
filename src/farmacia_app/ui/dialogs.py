from __future__ import annotations

from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QWidget, QMessageBox


def _center_widget_on_parent(widget: QWidget, parent: QWidget | None) -> None:
    widget.adjustSize()

    if parent is not None and parent.isVisible():
        p = parent.frameGeometry()
        widget.move(p.center() - widget.rect().center())
        return

    screen = QGuiApplication.primaryScreen()
    if screen is None:
        return
    geo = screen.availableGeometry()
    widget.move(geo.center() - widget.rect().center())


def info(parent: QWidget | None, title: str, text: str) -> None:
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Information)
    box.setWindowTitle(title)
    box.setText(text)
    box.setStandardButtons(QMessageBox.Ok)
    _center_widget_on_parent(box, parent)
    box.exec()


def warn(parent: QWidget | None, title: str, text: str) -> None:
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Warning)
    box.setWindowTitle(title)
    box.setText(text)
    box.setStandardButtons(QMessageBox.Ok)
    _center_widget_on_parent(box, parent)
    box.exec()


def question(parent: QWidget | None, title: str, text: str, default_no: bool = True) -> bool:
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Question)
    box.setWindowTitle(title)
    box.setText(text)
    box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
    box.setDefaultButton(QMessageBox.No if default_no else QMessageBox.Yes)
    _center_widget_on_parent(box, parent)
    return box.exec() == QMessageBox.Yes
