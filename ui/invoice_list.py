from pathlib import Path
from typing import List
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QScrollArea, QFrame,
    QHBoxLayout, QLabel, QPushButton
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QDragEnterEvent, QDropEvent
from core.models import Invoice, InvoiceStatus

SUPPORTED_SUFFIXES = {".pdf", ".jpg", ".jpeg", ".png"}

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
    clicked = pyqtSignal(str)   # file_path
    delete_requested = pyqtSignal(str)  # file_path

    def __init__(self, inv: Invoice, parent=None):
        super().__init__(parent)
        self.file_path = inv.file_path
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)

        # 左侧：文件名 + 识别时间
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(2)
        name = QLabel(inv.file_path.split("/")[-1])
        name.setWordWrap(True)
        left_layout.addWidget(name)
        if inv.created_at:
            time_label = QLabel(inv.created_at)
            time_label.setStyleSheet("color: #999; font-size: 11px;")
            left_layout.addWidget(time_label)
        layout.addWidget(left, 1)

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

        # 删除按钮
        del_btn = QPushButton("×")
        del_btn.setFixedSize(22, 22)
        del_btn.setStyleSheet(
            "QPushButton { background: transparent; color: #aaa; font-size: 16px; border: none; }"
            "QPushButton:hover { color: #e53935; }"
        )
        del_btn.setToolTip("删除此发票记录")
        del_btn.clicked.connect(lambda: self.delete_requested.emit(self.file_path))
        layout.addWidget(del_btn)

    def mousePressEvent(self, event):
        self.clicked.emit(self.file_path)


class InvoiceList(QWidget):
    invoice_selected = pyqtSignal(str)   # file_path
    invoice_delete = pyqtSignal(str)     # file_path
    files_dropped = pyqtSignal(list)     # list[Path]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 拖拽提示条（平时隐藏）
        self._drop_hint = QLabel("拖拽发票文件或文件夹到此处导入")
        self._drop_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._drop_hint.setStyleSheet(
            "background: #E3F2FD; color: #1565C0; padding: 12px; "
            "border: 2px dashed #90CAF9; border-radius: 6px; font-size: 13px;"
        )
        layout.addWidget(self._drop_hint)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll, 1)

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

        # 没有发票时显示拖拽提示，有发票时隐藏
        self._drop_hint.setVisible(len(invoices) == 0)

        for inv in invoices:
            card = InvoiceCard(inv)
            card.clicked.connect(self.invoice_selected)
            card.delete_requested.connect(self.invoice_delete)
            self._layout.addWidget(card)
            self._cards[inv.file_path] = card

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._drop_hint.setVisible(True)
            self._drop_hint.setStyleSheet(
                "background: #BBDEFB; color: #0D47A1; padding: 12px; "
                "border: 2px dashed #1565C0; border-radius: 6px; font-size: 13px; font-weight: bold;"
            )
            self._drop_hint.setText("松开鼠标即可导入")

    def dragLeaveEvent(self, event):
        # 恢复提示条状态
        has_cards = bool(self._cards)
        self._drop_hint.setVisible(not has_cards)
        self._drop_hint.setStyleSheet(
            "background: #E3F2FD; color: #1565C0; padding: 12px; "
            "border: 2px dashed #90CAF9; border-radius: 6px; font-size: 13px;"
        )
        self._drop_hint.setText("拖拽发票文件或文件夹到此处导入")

    def dropEvent(self, event: QDropEvent):
        self.dragLeaveEvent(event)
        paths: list[Path] = []
        for url in event.mimeData().urls():
            p = Path(url.toLocalFile())
            if p.is_dir():
                # 递归扫描文件夹，收集所有支持格式
                for f in p.rglob("*"):
                    if f.is_file() and f.suffix.lower() in SUPPORTED_SUFFIXES:
                        paths.append(f)
            elif p.is_file() and p.suffix.lower() in SUPPORTED_SUFFIXES:
                paths.append(p)
        if paths:
            self.files_dropped.emit(paths)
