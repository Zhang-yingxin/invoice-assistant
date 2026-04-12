# ui/reset_password_window.py
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit,
    QPushButton, QLabel, QStackedWidget, QWidget
)
from PyQt6.QtCore import pyqtSignal, Qt
from store.db import Database
from core.auth import AuthService
from core.mailer import Mailer


class ResetPasswordWindow(QDialog):
    reset_success = pyqtSignal()

    def __init__(self, db: Database, auth: AuthService, parent=None):
        super().__init__(parent)
        self._db = db
        self._auth = auth
        self._mailer = Mailer(db)
        self._email = ""
        self._step = 0
        self.setWindowTitle("忘记密码")
        self.setFixedWidth(380)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowTitleHint)

        layout = QVBoxLayout(self)
        self._stack = QStackedWidget()
        layout.addWidget(self._stack)

        # --- Step 0: 输入邮箱 ---
        page0 = QWidget()
        p0_layout = QVBoxLayout(page0)
        p0_layout.addWidget(QLabel("请输入注册时使用的邮箱："))
        self._email_input = QLineEdit()
        self._email_input.setPlaceholderText("邮箱地址")
        p0_layout.addWidget(self._email_input)
        self._p0_error = QLabel("")
        self._p0_error.setStyleSheet("color: red;")
        p0_layout.addWidget(self._p0_error)
        send_btn = QPushButton("发送验证码")
        send_btn.setStyleSheet(
            "QPushButton { background: #1E5BA8; color: white; border: none; "
            "border-radius: 4px; padding: 8px; }"
            "QPushButton:hover { background: #174d91; }"
        )
        send_btn.clicked.connect(self._send_code)
        p0_layout.addWidget(send_btn)
        self._stack.addWidget(page0)

        # --- Step 1: 输入验证码 ---
        page1 = QWidget()
        p1_layout = QVBoxLayout(page1)
        self._p1_hint = QLabel("")
        p1_layout.addWidget(self._p1_hint)
        self._code_input = QLineEdit()
        self._code_input.setPlaceholderText("6 位验证码")
        self._code_input.setMaxLength(6)
        p1_layout.addWidget(self._code_input)
        self._p1_error = QLabel("")
        self._p1_error.setStyleSheet("color: red;")
        p1_layout.addWidget(self._p1_error)
        verify_btn = QPushButton("验证")
        verify_btn.setStyleSheet(
            "QPushButton { background: #1E5BA8; color: white; border: none; "
            "border-radius: 4px; padding: 8px; }"
            "QPushButton:hover { background: #174d91; }"
        )
        verify_btn.clicked.connect(self._verify_code)
        p1_layout.addWidget(verify_btn)
        self._stack.addWidget(page1)

        # --- Step 2: 设置新密码 ---
        page2 = QWidget()
        p2_layout = QVBoxLayout(page2)
        form = QFormLayout()
        self._new_password = QLineEdit()
        self._new_password.setEchoMode(QLineEdit.EchoMode.Password)
        self._new_password.setPlaceholderText("新密码（至少 6 位）")
        form.addRow("新密码", self._new_password)
        self._new_confirm = QLineEdit()
        self._new_confirm.setEchoMode(QLineEdit.EchoMode.Password)
        self._new_confirm.setPlaceholderText("再次输入新密码")
        form.addRow("确认密码", self._new_confirm)
        p2_layout.addLayout(form)
        self._p2_error = QLabel("")
        self._p2_error.setStyleSheet("color: red;")
        p2_layout.addWidget(self._p2_error)
        reset_btn = QPushButton("重置密码")
        reset_btn.setStyleSheet(
            "QPushButton { background: #1E5BA8; color: white; border: none; "
            "border-radius: 4px; padding: 8px; }"
            "QPushButton:hover { background: #174d91; }"
        )
        reset_btn.clicked.connect(self._do_reset)
        p2_layout.addWidget(reset_btn)
        self._stack.addWidget(page2)

    def _send_code(self):
        email = self._email_input.text().strip()
        if not email:
            self._p0_error.setText("请输入邮箱")
            return
        if self._db.get_user_by_email(email) is None:
            self._p0_error.setText("该邮箱未注册")
            return
        code = self._auth.generate_reset_code(email)
        ok, msg = self._mailer.send_reset_code(email, code)
        if not ok:
            self._p0_error.setText(msg)
            return
        self._email = email
        self._p1_hint.setText(f"验证码已发送至 {email}，10 分钟内有效")
        self._p0_error.setText("")
        self._stack.setCurrentIndex(1)

    def _verify_code(self):
        code = self._code_input.text().strip()
        ok, msg = self._auth.verify_reset_code(self._email, code)
        if not ok:
            self._p1_error.setText(msg)
            return
        self._p1_error.setText("")
        self._stack.setCurrentIndex(2)

    def _do_reset(self):
        new_pw = self._new_password.text().strip()
        confirm = self._new_confirm.text().strip()
        if new_pw != confirm:
            self._p2_error.setText("两次输入的密码不一致")
            return
        if len(new_pw) < 6:
            self._p2_error.setText("密码长度不能少于 6 位")
            return
        ok, msg = self._auth.reset_password(self._email, new_pw)
        if ok:
            self.reset_success.emit()
            self.accept()
        else:
            self._p2_error.setText(msg)
