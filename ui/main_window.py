from PyQt6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt
from ui.sidebar import Sidebar
from store.db import Database


class MainWindow(QMainWindow):
    def __init__(self, db: Database):
        super().__init__()
        self._db = db
        self.setWindowTitle("发票识别登记助手")
        self.resize(1200, 800)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._sidebar = Sidebar()
        self._sidebar.nav_changed.connect(self._on_nav)
        layout.addWidget(self._sidebar)

        self._content = QLabel("内容区域（待实现）")
        self._content.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._content, 1)

    def _on_nav(self, key: str):
        self._content.setText(f"当前页: {key}")
