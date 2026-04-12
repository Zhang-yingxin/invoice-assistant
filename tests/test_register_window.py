# tests/test_register_window.py
import tempfile
from pathlib import Path
import pytest
from PyQt6.QtWidgets import QApplication
from store.db import Database
from core.auth import AuthService
from ui.register_window import RegisterWindow

@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_register_success_emits_signal(app, qtbot):
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Database(Path(tmpdir) / "test.db")
        auth = AuthService(db)
        win = RegisterWindow(db, auth)
        qtbot.addWidget(win)

        received = []
        win.register_success.connect(lambda: received.append(True))

        win._username.setText("newuser")
        win._email.setText("new@example.com")
        win._password.setText("Pass123!")
        win._confirm.setText("Pass123!")
        win._submit()

        assert len(received) == 1
        assert db.get_user_by_username("newuser") is not None


def test_register_password_mismatch(app, qtbot):
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Database(Path(tmpdir) / "test.db")
        auth = AuthService(db)
        win = RegisterWindow(db, auth)
        qtbot.addWidget(win)

        win._username.setText("user2")
        win._email.setText("user2@example.com")
        win._password.setText("Pass123!")
        win._confirm.setText("Different!")

        received = []
        win.register_success.connect(lambda: received.append(True))
        win._submit()

        assert len(received) == 0
        assert "不一致" in win._error_label.text()
