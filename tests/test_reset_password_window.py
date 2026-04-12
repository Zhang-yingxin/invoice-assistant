# tests/test_reset_password_window.py
import tempfile
from pathlib import Path
import pytest
from PyQt6.QtWidgets import QApplication
from store.db import Database
from core.auth import AuthService
from ui.reset_password_window import ResetPasswordWindow

@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_reset_password_flow(app, qtbot):
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Database(Path(tmpdir) / "test.db")
        auth = AuthService(db)
        auth.register("alice", "alice@example.com", "OldPass123")

        win = ResetPasswordWindow(db, auth)
        qtbot.addWidget(win)

        # Step 1: 输入邮箱（直接生成验证码，跳过发邮件）
        win._email_input.setText("alice@example.com")
        code = auth.generate_reset_code("alice@example.com")

        # Step 2: 直接设置内部状态，模拟已发送验证码
        win._step = 1
        win._email = "alice@example.com"
        win._stack.setCurrentIndex(1)
        win._code_input.setText(code)
        win._verify_code()

        # Step 3: 设置新密码
        assert win._stack.currentIndex() == 2
        win._new_password.setText("NewPass456!")
        win._new_confirm.setText("NewPass456!")

        received = []
        win.reset_success.connect(lambda: received.append(True))
        win._do_reset()

        assert len(received) == 1
        result = auth.login("alice", "NewPass456!")
        assert result["success"] is True
