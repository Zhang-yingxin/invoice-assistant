from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import pyqtSignal


class ProgressSummary(QWidget):
    bulk_confirm_clicked = pyqtSignal()
    cancel_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)

        self._summary = QLabel("共 0 张")
        layout.addWidget(self._summary)
        layout.addStretch()

        self._bulk_btn = QPushButton("批量确认")
        self._bulk_btn.setEnabled(False)
        self._bulk_btn.clicked.connect(self.bulk_confirm_clicked)
        layout.addWidget(self._bulk_btn)

        self._cancel_btn = QPushButton("取消识别")
        self._cancel_btn.hide()
        self._cancel_btn.clicked.connect(self.cancel_clicked)
        layout.addWidget(self._cancel_btn)

    def update_stats(self, total: int, confirmed: int, pending: int,
                     failed: int, total_amount: float, has_ocr_done: bool):
        self._summary.setText(
            f"共 {total} 张  |  已确认 {confirmed}  |  待处理 {pending}  "
            f"|  识别失败 {failed}  |  总金额 ¥{total_amount:,.2f}"
        )
        self._bulk_btn.setEnabled(has_ocr_done)

    def show_processing(self, current: int, total: int):
        self._summary.setText(f"正在识别 第 {current} 张 / 共 {total} 张")
        self._cancel_btn.show()
        self._bulk_btn.hide()

    def hide_processing(self):
        self._cancel_btn.hide()
        self._bulk_btn.show()
