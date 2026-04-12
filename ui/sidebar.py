from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton
from PyQt6.QtCore import pyqtSignal


class Sidebar(QWidget):
    nav_changed = pyqtSignal(str)

    def __init__(self, role: str = "user", parent=None):
        super().__init__(parent)
        self._role = role
        self.setFixedWidth(160)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 16, 8, 8)
        layout.setSpacing(4)

        self._btns = {}
        nav_items = [
            ("import", "导入发票"),
            ("import_folder", "批量导入文件夹"),
            ("phone_upload", "手机扫码上传"),
            ("pending", "待处理"),
            ("done", "已完成"),
            ("failed", "识别失败"),
            ("settings", "设置"),
        ]
        if role == "admin":
            nav_items.append(("user_management", "用户管理"))

        for key, label in nav_items:
            btn = QPushButton(label)
            if key in ("import", "import_folder", "phone_upload"):
                btn.setCheckable(False)
            else:
                btn.setCheckable(True)
            btn.clicked.connect(lambda checked, k=key: self._on_click(k))
            layout.addWidget(btn)
            self._btns[key] = btn

        layout.addStretch()
        self._btns["pending"].setChecked(True)

    def _on_click(self, key: str):
        if key not in ("import", "import_folder", "phone_upload"):
            for k, btn in self._btns.items():
                if k not in ("import", "import_folder", "phone_upload"):
                    btn.setChecked(k == key)
        self.nav_changed.emit(key)

    def update_counts(self, pending: int, done: int, failed: int):
        self._btns["pending"].setText(f"待处理 ({pending})")
        self._btns["done"].setText(f"已完成 ({done})")
        self._btns["failed"].setText(f"识别失败 ({failed})")
