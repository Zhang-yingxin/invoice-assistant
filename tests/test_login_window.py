# tests/test_login_window.py
import tempfile
from pathlib import Path
import pytest
from PyQt6.QtWidgets import QApplication
from store.db import Database
from core.auth import AuthService
from ui.login_window import LoginWindow

@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_login_success_emits_signal(app, qtbot):
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Database(Path(tmpdir) / "test.db")
        auth = AuthService(db)
        auth.register("alice", "alice@example.com", "Pass123!", role="user")

        win = LoginWindow(db, auth)
        qtbot.addWidget(win)

        received = []
        win.login_success.connect(lambda u: received.append(u))

        win._username.setText("alice")
        win._password.setText("Pass123!")
        win._do_login()

        assert len(received) == 1
        assert received[0]["username"] == "alice"


def test_login_wrong_password_shows_error(app, qtbot):
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Database(Path(tmpdir) / "test.db")
        auth = AuthService(db)
        auth.register("bob", "bob@example.com", "Pass123!", role="user")

        win = LoginWindow(db, auth)
        qtbot.addWidget(win)

        win._username.setText("bob")
        win._password.setText("WrongPass")
        win._do_login()

        assert win._error_label.text() != ""
