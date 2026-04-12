# tests/test_init_admin_window.py
import tempfile
from pathlib import Path
import pytest
from PyQt6.QtWidgets import QApplication
from store.db import Database
from core.auth import AuthService
from ui.init_admin_window import InitAdminWindow

@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_init_admin_window_creates_admin(app, qtbot):
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Database(Path(tmpdir) / "test.db")
        auth = AuthService(db)
        win = InitAdminWindow(db, auth)
        qtbot.addWidget(win)

        win._username.setText("admin")
        win._email.setText("admin@example.com")
        win._password.setText("Admin123!")
        win._confirm.setText("Admin123!")

        received = []
        win.admin_created.connect(lambda u: received.append(u))
        win._submit()

        assert len(received) == 1
        assert received[0]["username"] == "admin"
        assert received[0]["role"] == "admin"


def test_init_admin_password_mismatch(app, qtbot):
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Database(Path(tmpdir) / "test.db")
        auth = AuthService(db)
        win = InitAdminWindow(db, auth)
        qtbot.addWidget(win)

        win._username.setText("admin")
        win._email.setText("admin@example.com")
        win._password.setText("Admin123!")
        win._confirm.setText("Different!")

        received = []
        win.admin_created.connect(lambda u: received.append(u))
        win._submit()

        assert len(received) == 0
