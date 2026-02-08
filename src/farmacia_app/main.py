import sys

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication
from farmacia_app.ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    win = MainWindow()

    # Mostrar maximizada y centrada correctamente (Qt a veces necesita el event loop arrancado).
    def _show_centered_maximized() -> None:
        # si el usuario la mueve a otro monitor en el futuro, Qt ya gestiona esto.
        win.showMaximized()
        win.activateWindow()
        win.raise_()

    QTimer.singleShot(0, _show_centered_maximized)

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
