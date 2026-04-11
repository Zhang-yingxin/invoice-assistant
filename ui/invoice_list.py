from typing import List
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QScrollArea, QFrame,
    QHBoxLayout, QLabel
)
from PyQt6.QtCore import pyqtSignal, Qt
from core.models import Invoice, InvoiceStatus

STATUS_COLOR = {
    InvoiceStatus.PENDING: "#888888",
    InvoiceStatus.PROCESSING: "#2196F3",
    InvoiceStatus.OCR_DONE: "#FF9800",
    InvoiceStatus.CONFIRMED: "#4CAF50",
    InvoiceStatus.FAILED: "#F44336",
    InvoiceStatus.MANUAL_EDITING: "#9C27B0",
    InvoiceStatus.MANUAL_DONE: "#4CAF50",
}


class InvoiceCard(QFrame):
    clicked = pyqtSignal(str)  # file_path

    def __init__(self, inv: Invoice, parent=None):
        super().__init__(parent)
        self.file_path = inv.file_path
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        name = QLabel(inv.file_path.split("/")[-1])
        name.setWordWrap(True)
        layout.addWidget(name, 1)

        status_label = QLabel(inv.status.value)
        color = STATUS_COLOR.get(inv.status, "#888")
        status_label.setStyleSheet(f"color: {color}; font-weight: bold;")
        layout.addWidget(status_label)

        if inv.status == InvoiceStatus.MANUAL_DONE:
            tag = QLabel("手动")
            tag.setStyleSheet(
                "background: #9C27B0; color: white; padding: 2px 6px; border-radius: 3px;"
            )
            layout.addWidget(tag)

        # 跨历史批次重复警告
        if inv.error_message and inv.error_message.startswith("DUPLICATE:"):
            warn = QLabel("⚠ 重复")
            warn.setStyleSheet(
                "background: #FFC107; color: #333; padding: 2px 6px; border-radius: 3px;"
            )
            warn.setToolTip(inv.error_message.replace("DUPLICATE:", "").strip())
            layout.addWidget(warn)

    def mousePressEvent(self, event):
        self.clicked.emit(self.file_path)


class InvoiceList(QWidget):
    invoice_selected = pyqtSignal(str)  # file_path

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll)

        self._container = QWidget()
        self._layout = QVBoxLayout(self._container)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._layout.setSpacing(4)
        scroll.setWidget(self._container)

        self._cards: dict = {}

    def set_invoices(self, invoices: List[Invoice]):
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._cards.clear()

        for inv in invoices:
            card = InvoiceCard(inv)
            card.clicked.connect(self.invoice_selected)
            self._layout.addWidget(card)
            self._cards[inv.file_path] = card
