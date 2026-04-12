# ui/settings.py
from PyQt6.QtWidgets import (
    QWidget, QFormLayout, QLineEdit, QPushButton,
    QDoubleSpinBox, QFileDialog, QMessageBox, QVBoxLayout,
    QHBoxLayout, QLabel, QGroupBox, QComboBox
)
from PyQt6.QtCore import pyqtSignal
from store.db import Database

_REMEMBER_OPTIONS = [
    ("不记住（每次需登录）", 0),
    ("30 天", 30),
    ("60 天", 60),
    ("180 天", 180),
    ("365 天", 365),
    ("永久", -1),
]


class SettingsPage(QWidget):
    settings_saved = pyqtSignal()

    def __init__(self, db: Database, current_user: dict = None, parent=None):
        super().__init__(parent)
        self._db = db
        self._current_user = current_user or {}
        self._editing = False

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)

        # 顶部：标题 + 编辑按钮
        top_bar = QHBoxLayout()
        title = QLabel("设置")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        top_bar.addWidget(title)
        top_bar.addStretch()
        self._edit_btn = QPushButton("编辑")
        self._edit_btn.setStyleSheet(
            "QPushButton { color: #1E5BA8; border: 1px solid #1E5BA8; "
            "border-radius: 4px; padding: 4px 16px; }"
            "QPushButton:hover { background: #EBF0FA; }"
        )
        self._edit_btn.clicked.connect(self._toggle_edit)
        top_bar.addWidget(self._edit_btn)
        outer.addLayout(top_bar)

        # OCR 配置区块
        ocr_group = QGroupBox("OCR 配置（百度智能云）")
        ocr_form = QFormLayout(ocr_group)

        self._ak = QLineEdit()
        self._ak.setEchoMode(QLineEdit.EchoMode.Password)
        self._ak.setPlaceholderText("百度 API Key")
        ocr_form.addRow("API Key (AK)", self._ak)

        self._sk = QLineEdit()
        self._sk.setEchoMode(QLineEdit.EchoMode.Password)
        self._sk.setPlaceholderText("百度 Secret Key")
        ocr_form.addRow("Secret Key (SK)", self._sk)

        self._threshold = QDoubleSpinBox()
        self._threshold.setRange(0.8, 1.0)
        self._threshold.setSingleStep(0.01)
        self._threshold.setDecimals(2)
        ocr_form.addRow("置信度阈值", self._threshold)

        self._export_path = QLineEdit()
        ocr_form.addRow("默认导出路径", self._export_path)

        self._browse_btn = QPushButton("浏览...")
        self._browse_btn.clicked.connect(self._browse)
        ocr_form.addRow("", self._browse_btn)
        outer.addWidget(ocr_group)

        # SMTP 配置区块
        smtp_group = QGroupBox("邮件配置（SMTP，用于密码重置验证码）")
        smtp_form = QFormLayout(smtp_group)

        self._smtp_host = QLineEdit()
        self._smtp_host.setPlaceholderText("如：smtp.qq.com")
        smtp_form.addRow("SMTP 服务器", self._smtp_host)

        self._smtp_port = QLineEdit()
        self._smtp_port.setPlaceholderText("465")
        smtp_form.addRow("端口", self._smtp_port)

        self._smtp_user = QLineEdit()
        self._smtp_user.setPlaceholderText("发件邮箱地址")
        smtp_form.addRow("发件邮箱", self._smtp_user)

        self._smtp_password = QLineEdit()
        self._smtp_password.setEchoMode(QLineEdit.EchoMode.Password)
        self._smtp_password.setPlaceholderText("邮箱授权码")
        smtp_form.addRow("授权码", self._smtp_password)

        outer.addWidget(smtp_group)

        # 账号安全区块
        acct_group = QGroupBox("账号安全")
        acct_form = QFormLayout(acct_group)

        self._remember_combo = QComboBox()
        for label, _ in _REMEMBER_OPTIONS:
            self._remember_combo.addItem(label)
        saved_days = self._db.get_setting("remember_login_days", "0")
        for i, (_, days) in enumerate(_REMEMBER_OPTIONS):
            if str(days) == saved_days:
                self._remember_combo.setCurrentIndex(i)
                break
        acct_form.addRow("免登录时长", self._remember_combo)

        save_remember_btn = QPushButton("应用")
        save_remember_btn.setFixedWidth(80)
        save_remember_btn.clicked.connect(self._save_remember)
        acct_form.addRow("", save_remember_btn)
        outer.addWidget(acct_group)

        # 修改密码区块
        pw_group = QGroupBox("修改密码")
        pw_form = QFormLayout(pw_group)

        self._old_pw = QLineEdit()
        self._old_pw.setEchoMode(QLineEdit.EchoMode.Password)
        self._old_pw.setPlaceholderText("当前密码")
        pw_form.addRow("当前密码", self._old_pw)

        self._new_pw = QLineEdit()
        self._new_pw.setEchoMode(QLineEdit.EchoMode.Password)
        self._new_pw.setPlaceholderText("新密码（至少 6 位）")
        pw_form.addRow("新密码", self._new_pw)

        self._new_pw_confirm = QLineEdit()
        self._new_pw_confirm.setEchoMode(QLineEdit.EchoMode.Password)
        self._new_pw_confirm.setPlaceholderText("再次输入新密码")
        pw_form.addRow("确认新密码", self._new_pw_confirm)

        self._change_pw_btn = QPushButton("修改密码")
        self._change_pw_btn.clicked.connect(self._change_password)
        pw_form.addRow("", self._change_pw_btn)
        outer.addWidget(pw_group)

        # 保存按钮
        self._save_btn = QPushButton("保存设置")
        self._save_btn.setStyleSheet(
            "QPushButton { background: #1E5BA8; color: white; border: none; "
            "border-radius: 4px; padding: 8px; font-size: 14px; }"
            "QPushButton:hover { background: #174d91; }"
        )
        self._save_btn.clicked.connect(self._save)
        outer.addWidget(self._save_btn)
        outer.addStretch()

        self._all_fields = [
            self._ak, self._sk, self._export_path,
            self._smtp_host, self._smtp_port, self._smtp_user, self._smtp_password,
        ]
        self._load()
        self._set_readonly(True)

    def _set_readonly(self, readonly: bool):
        for field in self._all_fields:
            field.setReadOnly(readonly)
        self._threshold.setReadOnly(readonly)
        self._browse_btn.setEnabled(not readonly)
        self._save_btn.setEnabled(not readonly)
        self._change_pw_btn.setEnabled(not readonly)
        self._old_pw.setReadOnly(readonly)
        self._new_pw.setReadOnly(readonly)
        self._new_pw_confirm.setReadOnly(readonly)
        style = "background: #F5F5F5;" if readonly else ""
        for field in self._all_fields:
            field.setStyleSheet(style)

    def _toggle_edit(self):
        self._editing = not self._editing
        self._set_readonly(not self._editing)
        self._edit_btn.setText("取消" if self._editing else "编辑")

    def _load(self):
        self._ak.setText(self._db.get_setting("api_key", ""))
        self._sk.setText(self._db.get_setting("secret_key", ""))
        self._threshold.setValue(float(self._db.get_setting("confidence_threshold", "0.9")))
        self._export_path.setText(self._db.get_setting("export_path", ""))
        self._smtp_host.setText(self._db.get_setting("smtp_host", ""))
        self._smtp_port.setText(self._db.get_setting("smtp_port", "465"))
        self._smtp_user.setText(self._db.get_setting("smtp_user", ""))
        self._smtp_password.setText(self._db.get_setting("smtp_password", ""))

    def _browse(self):
        path = QFileDialog.getExistingDirectory(self, "选择默认导出目录")
        if path:
            self._export_path.setText(path)

    def _save(self):
        self._db.set_setting("api_key", self._ak.text().strip())
        self._db.set_setting("secret_key", self._sk.text().strip())
        self._db.set_setting("confidence_threshold", str(self._threshold.value()))
        self._db.set_setting("export_path", self._export_path.text().strip())
        self._db.set_setting("smtp_host", self._smtp_host.text().strip())
        self._db.set_setting("smtp_port", self._smtp_port.text().strip() or "465")
        self._db.set_setting("smtp_user", self._smtp_user.text().strip())
        self._db.set_setting("smtp_password", self._smtp_password.text().strip())
        self._db.set_setting("smtp_ssl", "true")
        QMessageBox.information(self, "设置", "保存成功")
        self._editing = False
        self._set_readonly(True)
        self._edit_btn.setText("编辑")
        self.settings_saved.emit()

    def _save_remember(self):
        idx = self._remember_combo.currentIndex()
        _, days = _REMEMBER_OPTIONS[idx]
        self._db.set_setting("remember_login_days", str(days))
        # 同步更新当前已有的自动登录凭据过期时间
        uid_str = self._db.get_setting("auto_login_user_id", "")
        if uid_str:
            from ui.login_window import _save_auto_login
            try:
                _save_auto_login(self._db, int(uid_str), days)
            except (ValueError, TypeError):
                pass
        QMessageBox.information(self, "免登录", "免登录设置已更新，下次登录时生效")

    def _change_password(self):
        if not self._current_user:
            return
        from core.auth import AuthService
        auth = AuthService(self._db)
        old_pw = self._old_pw.text()
        new_pw = self._new_pw.text()
        confirm = self._new_pw_confirm.text()
        if not old_pw or not new_pw:
            QMessageBox.warning(self, "修改密码", "请填写当前密码和新密码")
            return
        if new_pw != confirm:
            QMessageBox.warning(self, "修改密码", "两次输入的新密码不一致")
            return
        if len(new_pw) < 6:
            QMessageBox.warning(self, "修改密码", "新密码长度不能少于 6 位")
            return
        ok, msg = auth.change_password(self._current_user["id"], old_pw, new_pw)
        if ok:
            QMessageBox.information(self, "修改密码", "密码修改成功")
            self._old_pw.clear()
            self._new_pw.clear()
            self._new_pw_confirm.clear()
        else:
            QMessageBox.warning(self, "修改密码", msg)
