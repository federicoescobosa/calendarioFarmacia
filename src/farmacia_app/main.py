import sys
from PySide6.QtWidgets import QApplication
from farmacia_app.ui.main_window import MainWindow
from datetime import date
from farmacia_app.data.holidays_repository import HolidaysRepository



def main() -> int:
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

# Festivos: ES + Andalucía
repo = HolidaysRepository()
y = date.today().year
repo.ensure_year(country_code="ES", subdivision_code="ES-AN", year=y)
repo.ensure_year(country_code="ES", subdivision_code="ES-AN", year=y + 1)
