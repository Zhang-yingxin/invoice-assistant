from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import pyqtSignal


class ProgressSummary(QWidget):
    bulk_confirm_clicked = pyqtSignal()
    cancel_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            "background: #FFFFFF; border-bottom: 1px solid #E0E0E0;"
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(16)

        self._summary = QLabel("暂无发票")
        self._summary.setStyleSheet("color: #666; font-size: 13px;")
        layout.addWidget(self._summary)
        layout.addStretch()

        self._bulk_btn = QPushButton("批量确认")
        self._bulk_btn.setEnabled(False)
        self._bulk_btn.setFixedHeight(32)
        self._bulk_btn.setStyleSheet("""
            QPushButton {
                background: #1E5BA8; color: white; border: none;
                border-radius: 4px; padding: 0 16px; font-size: 13px;
            }
            QPushButton:hover { background: #0D47A1; }
            QPushButton:disabled { background: #E0E0E0; color: #AAAAAA; }
        """)
        self._bulk_btn.setToolTip("当前没有可批量确认的发票（需先成功识别发票）")
        self._bulk_btn.clicked.connect(self.bulk_confirm_clicked)
        layout.addWidget(self._bulk_btn)

        self._cancel_btn = QPushButton("取消识别")
        self._cancel_btn.hide()
        self._cancel_btn.setFixedHeight(32)
        self._cancel_btn.setStyleSheet("""
            QPushButton {
                background: #F5F5F5; color: #666; border: 1px solid #E0E0E0;
                border-radius: 4px; padding: 0 16px; font-size: 13px;
            }
            QPushButton:hover { background: #EEEEEE; color: #333; }
        """)
        self._cancel_btn.clicked.connect(self.cancel_clicked)
        layout.addWidget(self._cancel_btn)

    def update_stats(self, total: int, confirmed: int, pending: int,
                     failed: int, total_amount: float, has_ocr_done: bool):
        parts = []
        if total: parts.append(f"共 <b>{total}</b> 张")
        if confirmed: parts.append(f"已确认 <b style='color:#388E3C'>{confirmed}</b>")
        if pending: parts.append(f"待处理 <b style='color:#FF9800'>{pending}</b>")
        if failed: parts.append(f"失败 <b style='color:#D32F2F'>{failed}</b>")
        if total_amount: parts.append(f"总金额 <b>¥{total_amount:,.2f}</b>")
        self._summary.setText("  |  ".join(parts) if parts else "暂无发票")
        self._bulk_btn.setEnabled(has_ocr_done)
        if has_ocr_done:
            self._bulk_btn.setToolTip("")
        else:
            self._bulk_btn.setToolTip("当前没有可批量确认的发票（需先成功识别发票）")

    def show_processing(self, current: int, total: int):
        self._summary.setText(f"正在识别  <b>{current}</b> / {total}  张  （每秒2张）")
        self._cancel_btn.show()
        self._bulk_btn.hide()

    def hide_processing(self):
        self._cancel_btn.hide()
        self._bulk_btn.show()
