# ui/login_window.py
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit,
    QPushButton, QLabel, QHBoxLayout, QComboBox
)
from PyQt6.QtCore import pyqtSignal, Qt
from store.db import Database
from core.auth import AuthService

# 免登录选项：显示文字 → 天数（0 = 不记住，-1 = 永久）
_REMEMBER_OPTIONS = [
    ("不记住", 0),
    ("30 天", 30),
    ("60 天", 60),
    ("180 天", 180),
    ("365 天", 365),
    ("永久", -1),
]


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

        # 免登录选择
        self._remember_combo = QComboBox()
        for label, _ in _REMEMBER_OPTIONS:
            self._remember_combo.addItem(label)
        # 默认选上次使用的选项
        saved_days = db.get_setting("remember_login_days", "0")
        for i, (_, days) in enumerate(_REMEMBER_OPTIONS):
            if str(days) == saved_days:
                self._remember_combo.setCurrentIndex(i)
                break
        form.addRow("免登录", self._remember_combo)

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
            user = result["user"]
            # 保存免登录状态
            idx = self._remember_combo.currentIndex()
            _, days = _REMEMBER_OPTIONS[idx]
            self._db.set_setting("remember_login_days", str(days))
            _save_auto_login(self._db, user["id"], days)
            self.login_success.emit(user)
            self.accept()
        else:
            self._error_label.setText(result["message"])


def _save_auto_login(db: Database, user_id: int, days: int):
    """保存自动登录凭据。days=0 清除，days=-1 永久，其他为天数。"""
    import time
    if days == 0:
        db.set_setting("auto_login_user_id", "")
        db.set_setting("auto_login_expire", "")
    elif days == -1:
        db.set_setting("auto_login_user_id", str(user_id))
        db.set_setting("auto_login_expire", "0")  # 0 = 永久
    else:
        expire_ts = int(time.time()) + days * 86400
        db.set_setting("auto_login_user_id", str(user_id))
        db.set_setting("auto_login_expire", str(expire_ts))


def check_auto_login(db: Database):
    """检查是否有有效的自动登录凭据，有则返回用户 dict，否则返回 None。"""
    import time
    uid_str = db.get_setting("auto_login_user_id", "")
    expire_str = db.get_setting("auto_login_expire", "")
    if not uid_str:
        return None
    try:
        user_id = int(uid_str)
        expire_ts = int(expire_str)
    except (ValueError, TypeError):
        return None
    # expire_ts == 0 表示永久
    if expire_ts != 0 and time.time() > expire_ts:
        # 已过期，清除
        db.set_setting("auto_login_user_id", "")
        db.set_setting("auto_login_expire", "")
        return None
    # 查找用户
    user = db.get_user_by_id(user_id)
    if user is None or not user.get("is_active", True):
        db.set_setting("auto_login_user_id", "")
        db.set_setting("auto_login_expire", "")
        return None
    return user
