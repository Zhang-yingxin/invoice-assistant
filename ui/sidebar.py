from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QFrame
from PyQt6.QtCore import pyqtSignal


class Sidebar(QWidget):
    nav_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(168)
        self.setStyleSheet("background: #1E3A5F;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # App title
        title = QLabel("发票助手")
        title.setStyleSheet(
            "color: white; font-size: 16px; font-weight: bold;"
            "padding: 20px 16px 16px 16px;"
        )
        layout.addWidget(title)

        # Divider
        div1 = QFrame()
        div1.setFrameShape(QFrame.Shape.HLine)
        div1.setStyleSheet("background: rgba(255,255,255,0.15); max-height: 1px;")
        layout.addWidget(div1)

        # Import section label
        import_label = QLabel("导入")
        import_label.setStyleSheet(
            "color: rgba(255,255,255,0.5); font-size: 11px; "
            "padding: 12px 16px 4px 16px; letter-spacing: 1px;"
        )
        layout.addWidget(import_label)

        self._btns = {}
        import_btns = [
            ("import", "导入发票"),
            ("import_folder", "批量导入文件夹"),
        ]
        for key, label in import_btns:
            btn = self._make_btn(key, label, checkable=False)
            layout.addWidget(btn)

        # Divider
        div2 = QFrame()
        div2.setFrameShape(QFrame.Shape.HLine)
        div2.setStyleSheet("background: rgba(255,255,255,0.15); max-height: 1px; margin: 8px 0;")
        layout.addWidget(div2)

        # Status filter label
        status_label = QLabel("状态筛选")
        status_label.setStyleSheet(
            "color: rgba(255,255,255,0.5); font-size: 11px; "
            "padding: 4px 16px 4px 16px; letter-spacing: 1px;"
        )
        layout.addWidget(status_label)

        filter_btns = [
            ("pending", "待处理"),
            ("done", "已完成"),
            ("failed", "识别失败"),
        ]
        for key, label in filter_btns:
            btn = self._make_btn(key, label, checkable=True)
            layout.addWidget(btn)

        layout.addStretch()

        # Divider
        div3 = QFrame()
        div3.setFrameShape(QFrame.Shape.HLine)
        div3.setStyleSheet("background: rgba(255,255,255,0.15); max-height: 1px;")
        layout.addWidget(div3)

        settings_btn = self._make_btn("settings", "设置", checkable=True)
        layout.addWidget(settings_btn)

        self._btns["pending"].setChecked(True)

    def _make_btn(self, key: str, label: str, checkable: bool) -> QPushButton:
        btn = QPushButton(label)
        btn.setCheckable(checkable)
        btn.setFixedHeight(40)
        btn.setStyleSheet("""
            QPushButton {
                color: rgba(255,255,255,0.75);
                background: transparent;
                border: none;
                text-align: left;
                padding: 0 16px;
                font-size: 13px;
            }
            QPushButton:hover {
                background: rgba(255,255,255,0.1);
                color: white;
            }
            QPushButton:checked {
                background: rgba(255,255,255,0.15);
                color: white;
                font-weight: bold;
                border-left: 3px solid #90CAF9;
                padding-left: 13px;
            }
        """)
        btn.clicked.connect(lambda checked, k=key: self._on_click(k))
        self._btns[key] = btn
        return btn

    def _on_click(self, key: str):
        if key not in ("import", "import_folder"):
            for k, btn in self._btns.items():
                if k not in ("import", "import_folder"):
                    btn.setChecked(k == key)
        self.nav_changed.emit(key)

    def update_counts(self, pending: int, done: int, failed: int):
        self._btns["pending"].setText(f"待处理  {pending}" if pending else "待处理")
        self._btns["done"].setText(f"已完成  {done}" if done else "已完成")
        self._btns["failed"].setText(f"识别失败  {failed}" if failed else "识别失败")
