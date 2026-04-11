from PyQt6.QtWidgets import (
    QWidget, QFormLayout, QLineEdit, QPushButton,
    QDoubleSpinBox, QFileDialog, QMessageBox, QVBoxLayout
)
from PyQt6.QtCore import pyqtSignal
from store.db import Database


class SettingsPage(QWidget):
    settings_saved = pyqtSignal()

    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self._db = db
        layout = QVBoxLayout(self)
        form = QFormLayout()
        layout.addLayout(form)

        self._ak = QLineEdit()
        self._ak.setEchoMode(QLineEdit.EchoMode.Password)
        self._ak.setPlaceholderText("百度 API Key")
        form.addRow("API Key (AK)", self._ak)

        self._sk = QLineEdit()
        self._sk.setEchoMode(QLineEdit.EchoMode.Password)
        self._sk.setPlaceholderText("百度 Secret Key")
        form.addRow("Secret Key (SK)", self._sk)

        self._threshold = QDoubleSpinBox()
        self._threshold.setRange(0.8, 1.0)
        self._threshold.setSingleStep(0.01)
        self._threshold.setDecimals(2)
        form.addRow("置信度阈值", self._threshold)

        self._export_path = QLineEdit()
        form.addRow("默认导出路径", self._export_path)

        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self._browse)
        form.addRow("", browse_btn)

        save_btn = QPushButton("保存设置")
        save_btn.clicked.connect(self._save)
        layout.addWidget(save_btn)
        layout.addStretch()

        self._load()

    def _load(self):
        self._ak.setText(self._db.get_setting("api_key", ""))
        self._sk.setText(self._db.get_setting("secret_key", ""))
        self._threshold.setValue(float(self._db.get_setting("confidence_threshold", "0.9")))
        self._export_path.setText(self._db.get_setting("export_path", ""))

    def _browse(self):
        path = QFileDialog.getExistingDirectory(self, "选择默认导出目录")
        if path:
            self._export_path.setText(path)

    def _save(self):
        self._db.set_setting("api_key", self._ak.text().strip())
        self._db.set_setting("secret_key", self._sk.text().strip())
        self._db.set_setting("confidence_threshold", str(self._threshold.value()))
        self._db.set_setting("export_path", self._export_path.text().strip())
        QMessageBox.information(self, "设置", "保存成功")
        self.settings_saved.emit()
