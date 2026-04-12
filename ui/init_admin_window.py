# ui/init_admin_window.py
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit,
    QPushButton, QLabel
)
from PyQt6.QtCore import pyqtSignal, Qt
from store.db import Database
from core.auth import AuthService


class InitAdminWindow(QDialog):
    admin_created = pyqtSignal(dict)  # 发射创建好的管理员用户 dict

    def __init__(self, db: Database, auth: AuthService, parent=None):
        super().__init__(parent)
        self._db = db
        self._auth = auth
        self.setWindowTitle("初始化管理员账号")
        self.setFixedWidth(360)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowTitleHint)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title = QLabel("首次启动，请创建管理员账号")
        title.setStyleSheet("font-size: 15px; font-weight: bold;")
        layout.addWidget(title)

        form = QFormLayout()
        self._username = QLineEdit()
        self._username.setPlaceholderText("用户名")
        form.addRow("用户名", self._username)

        self._email = QLineEdit()
        self._email.setPlaceholderText("邮箱（用于找回密码）")
        form.addRow("邮箱", self._email)

        self._password = QLineEdit()
        self._password.setEchoMode(QLineEdit.EchoMode.Password)
        self._password.setPlaceholderText("密码")
        form.addRow("密码", self._password)

        self._confirm = QLineEdit()
        self._confirm.setEchoMode(QLineEdit.EchoMode.Password)
        self._confirm.setPlaceholderText("再次输入密码")
        form.addRow("确认密码", self._confirm)

        layout.addLayout(form)

        self._error_label = QLabel("")
        self._error_label.setStyleSheet("color: red;")
        self._error_label.setWordWrap(True)
        layout.addWidget(self._error_label)

        submit_btn = QPushButton("创建管理员账号")
        submit_btn.setStyleSheet(
            "QPushButton { background: #1E5BA8; color: white; border: none; "
            "border-radius: 4px; padding: 8px; font-size: 14px; }"
            "QPushButton:hover { background: #174d91; }"
        )
        submit_btn.clicked.connect(self._submit)
        layout.addWidget(submit_btn)

    def _submit(self):
        username = self._username.text().strip()
        email = self._email.text().strip()
        password = self._password.text().strip()
        confirm = self._confirm.text().strip()

        if not username or not email or not password:
            self._error_label.setText("所有字段均为必填项")
            return
        if password != confirm:
            self._error_label.setText("两次输入的密码不一致")
            return
        if len(password) < 6:
            self._error_label.setText("密码长度不能少于 6 位")
            return

        ok, msg = self._auth.register(username, email, password, role="admin")
        if not ok:
            self._error_label.setText(msg)
            return

        user = self._db.get_user_by_username(username)
        self.admin_created.emit(user)
        self.accept()
