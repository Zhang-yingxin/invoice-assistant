# ui/login_window.py
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit,
    QPushButton, QLabel, QHBoxLayout
)
from PyQt6.QtCore import pyqtSignal, Qt
from store.db import Database
from core.auth import AuthService


class LoginWindow(QDialog):
    login_success = pyqtSignal(dict)
    register_requested = pyqtSignal()
    forgot_password_requested = pyqtSignal()

    def __init__(self, db: Database, auth: AuthService, parent=None):
        super().__init__(parent)
        self._db = db
        self._auth = auth
        self.setWindowTitle("发票助手 — 登录")
        self.setFixedWidth(360)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowTitleHint)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title = QLabel("欢迎使用发票助手")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        form = QFormLayout()
        self._username = QLineEdit()
        self._username.setPlaceholderText("用户名")
        form.addRow("用户名", self._username)

        self._password = QLineEdit()
        self._password.setEchoMode(QLineEdit.EchoMode.Password)
        self._password.setPlaceholderText("密码")
        self._password.returnPressed.connect(self._do_login)
        form.addRow("密码", self._password)

        layout.addLayout(form)

        self._error_label = QLabel("")
        self._error_label.setStyleSheet("color: red;")
        self._error_label.setWordWrap(True)
        layout.addWidget(self._error_label)

        login_btn = QPushButton("登录")
        login_btn.setStyleSheet(
            "QPushButton { background: #1E5BA8; color: white; border: none; "
            "border-radius: 4px; padding: 8px; font-size: 14px; }"
            "QPushButton:hover { background: #174d91; }"
        )
        login_btn.clicked.connect(self._do_login)
        layout.addWidget(login_btn)

        bottom = QHBoxLayout()
        reg_btn = QPushButton("注册账号")
        reg_btn.setFlat(True)
        reg_btn.setStyleSheet("color: #1E5BA8;")
        reg_btn.clicked.connect(self.register_requested.emit)
        bottom.addWidget(reg_btn)

        bottom.addStretch()

        forgot_btn = QPushButton("忘记密码")
        forgot_btn.setFlat(True)
        forgot_btn.setStyleSheet("color: #1E5BA8;")
        forgot_btn.clicked.connect(self.forgot_password_requested.emit)
        bottom.addWidget(forgot_btn)

        layout.addLayout(bottom)

    def _do_login(self):
        username = self._username.text().strip()
        password = self._password.text()
        if not username or not password:
            self._error_label.setText("请输入用户名和密码")
            return
        result = self._auth.login(username, password)
        if result["success"]:
            self._error_label.setText("")
            self.login_success.emit(result["user"])
            self.accept()
        else:
            self._error_label.setText(result["message"])
