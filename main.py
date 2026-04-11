import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from store.db import Database
from ui.main_window import MainWindow

DB_PATH = Path.home() / ".invoice_assistant" / "data.db"


def main():
    app = QApplication(sys.argv)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = Database(DB_PATH)
    window = MainWindow(db)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
