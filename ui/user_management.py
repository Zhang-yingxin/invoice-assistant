# ui/user_management.py
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHeaderView, QMessageBox
)
from PyQt6.QtCore import Qt
from store.db import Database
from core.auth import AuthService


class UserManagementPage(QWidget):
    def __init__(self, db: Database, auth: AuthService, parent=None):
        super().__init__(parent)
        self._db = db
        self._auth = auth

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)

        title = QLabel("用户管理")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        self._table = QTableWidget()
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels(["ID", "用户名", "邮箱", "角色", "状态"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self._table)

        btn_row = QHBoxLayout()
        self._toggle_btn = QPushButton("禁用/启用")
        self._toggle_btn.clicked.connect(self._toggle_active)
        btn_row.addWidget(self._toggle_btn)

        self._reset_btn = QPushButton("重置密码")
        self._reset_btn.clicked.connect(self._reset_password)
        btn_row.addWidget(self._reset_btn)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        self._refresh()

    def _refresh(self):
        users = self._db.get_all_users()
        self._table.setRowCount(len(users))
        for row, u in enumerate(users):
            self._table.setItem(row, 0, QTableWidgetItem(str(u["id"])))
            self._table.setItem(row, 1, QTableWidgetItem(u["username"]))
            self._table.setItem(row, 2, QTableWidgetItem(u["email"]))
            self._table.setItem(row, 3, QTableWidgetItem(u["role"]))
            status_text = "正常" if u["is_active"] else "已禁用"
            item = QTableWidgetItem(status_text)
            if not u["is_active"]:
                item.setForeground(Qt.GlobalColor.red)
            self._table.setItem(row, 4, item)

    def _selected_user_id(self):
        row = self._table.currentRow()
        if row < 0:
            return None
        item = self._table.item(row, 0)
        return int(item.text()) if item else None

    def _toggle_active(self):
        uid = self._selected_user_id()
        if uid is None:
            QMessageBox.information(self, "提示", "请先选择一个用户")
            return
        users = self._db.get_all_users()
        user = next((u for u in users if u["id"] == uid), None)
        if user is None:
            return
        if user["role"] == "admin":
            QMessageBox.warning(self, "提示", "不能禁用管理员账号")
            return
        new_state = not user["is_active"]
        action = "启用" if new_state else "禁用"
        reply = QMessageBox.question(self, "确认", f"确认{action}用户 {user['username']}？")
        if reply == QMessageBox.StandardButton.Yes:
            self._db.set_user_active(uid, new_state)
            self._refresh()

    def _reset_password(self):
        import bcrypt
        uid = self._selected_user_id()
        if uid is None:
            QMessageBox.information(self, "提示", "请先选择一个用户")
            return
        users = self._db.get_all_users()
        user = next((u for u in users if u["id"] == uid), None)
        if user is None:
            return
        new_pw = "Aa123456"
        new_hash = bcrypt.hashpw(new_pw.encode(), bcrypt.gensalt()).decode()
        self._db.update_user_password(uid, new_hash)
        QMessageBox.information(
            self, "重置成功",
            f"用户 {user['username']} 的密码已重置为：{new_pw}\n请通知用户登录后修改密码。"
        )
