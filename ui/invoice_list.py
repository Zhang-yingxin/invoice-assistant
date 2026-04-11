from pathlib import Path
from typing import List
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QScrollArea, QFrame,
    QHBoxLayout, QLabel, QPushButton, QCheckBox
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QDragEnterEvent, QDropEvent
from core.models import Invoice, InvoiceStatus

SUPPORTED_SUFFIXES = {".pdf", ".jpg", ".jpeg", ".png"}

STATUS_COLOR = {
    InvoiceStatus.PENDING: "#666666",
    InvoiceStatus.PROCESSING: "#1E5BA8",
    InvoiceStatus.OCR_DONE: "#FF9800",
    InvoiceStatus.CONFIRMED: "#388E3C",
    InvoiceStatus.FAILED: "#D32F2F",
    InvoiceStatus.MANUAL_EDITING: "#9C27B0",
    InvoiceStatus.MANUAL_DONE: "#388E3C",
}


class InvoiceCard(QFrame):
    clicked = pyqtSignal(str)           # file_path
    delete_requested = pyqtSignal(str)  # file_path
    check_changed = pyqtSignal(str, bool)  # file_path, checked

    def __init__(self, inv: Invoice, parent=None):
        super().__init__(parent)
        self.file_path = inv.file_path
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 8, 8)
        layout.setSpacing(8)
        self.setStyleSheet("""
            QFrame { background: #FFFFFF; border: 1px solid #E8E8E8; border-radius: 6px; }
            QFrame:hover { background: #F8F9FF; border-color: #90CAF9; }
        """)
        self.setMinimumHeight(56)

        # Checkbox
        self._checkbox = QCheckBox()
        self._checkbox.setFixedWidth(18)
        self._checkbox.stateChanged.connect(
            lambda state: self.check_changed.emit(self.file_path, state == 2)
        )
        layout.addWidget(self._checkbox)

        # Center: filename + time
        center = QWidget()
        center.setStyleSheet("border: none; background: transparent;")
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(2)

        filename = inv.file_path.split("/")[-1]
        name = QLabel(filename)
        name.setStyleSheet("font-size: 13px; color: #212121; font-weight: 500; border: none;")
        name.setMaximumWidth(200)
        name.setToolTip(inv.file_path)
        # Truncate with ellipsis if too long
        if len(filename) > 28:
            name.setText(filename[:25] + "…")
        center_layout.addWidget(name)

        if inv.created_at:
            time_label = QLabel(inv.created_at)
            time_label.setStyleSheet("color: #999; font-size: 11px; border: none;")
            center_layout.addWidget(time_label)
        layout.addWidget(center, 1)

        # Status badge
        status_label = QLabel(inv.status.value)
        color = STATUS_COLOR.get(inv.status, "#888")
        status_label.setStyleSheet(
            f"color: {color}; font-size: 12px; font-weight: bold; border: none;"
            f"background: transparent;"
        )
        layout.addWidget(status_label)

        if inv.status == InvoiceStatus.MANUAL_DONE:
            tag = QLabel("手动")
            tag.setStyleSheet(
                "background: #9C27B0; color: white; padding: 1px 5px;"
                "border-radius: 3px; font-size: 11px; border: none;"
            )
            layout.addWidget(tag)

        if inv.error_message and inv.error_message.startswith("DUPLICATE:"):
            warn = QLabel("重复")
            warn.setStyleSheet(
                "background: #FFF3CD; color: #856404; padding: 1px 5px;"
                "border-radius: 3px; font-size: 11px; border: 1px solid #FFE082;"
            )
            warn.setToolTip(inv.error_message.replace("DUPLICATE:", "").strip())
            layout.addWidget(warn)

        del_btn = QPushButton("×")
        del_btn.setFixedSize(20, 20)
        del_btn.setStyleSheet("""
            QPushButton { background: transparent; color: #CCCCCC; font-size: 15px;
                          border: none; border-radius: 3px; padding: 0; }
            QPushButton:hover { color: #D32F2F; background: #FFEBEE; }
        """)
        del_btn.setToolTip("删除此记录")
        del_btn.clicked.connect(lambda: self.delete_requested.emit(self.file_path))
        layout.addWidget(del_btn)

    def set_checked(self, checked: bool):
        self._checkbox.blockSignals(True)
        self._checkbox.setChecked(checked)
        self._checkbox.blockSignals(False)

    def is_checked(self) -> bool:
        return self._checkbox.isChecked()

    def mousePressEvent(self, event):
        # 点击卡片主体区域时触发 clicked（不拦截复选框自身的点击）
        if not self._checkbox.geometry().contains(event.pos()):
            self.clicked.emit(self.file_path)


class InvoiceList(QWidget):
    invoice_selected = pyqtSignal(str)    # file_path
    invoice_delete = pyqtSignal(str)      # file_path
    invoices_delete_batch = pyqtSignal(list)  # list[str] file_paths
    files_dropped = pyqtSignal(list)      # list[Path]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 全选/删除工具栏
        toolbar = QWidget()
        toolbar.setStyleSheet("background: #FAFAFA; border-bottom: 1px solid #E8E8E8;")
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(8, 4, 8, 4)
        tb_layout.setSpacing(6)
        self._select_all_cb = QCheckBox("全选")
        self._select_all_cb.stateChanged.connect(self._on_select_all)
        tb_layout.addWidget(self._select_all_cb)
        tb_layout.addStretch()
        self._del_selected_btn = QPushButton("删除所选")
        self._del_selected_btn.setEnabled(False)
        self._del_selected_btn.setStyleSheet(
            "QPushButton { color: #e53935; } QPushButton:disabled { color: #ccc; }"
        )
        self._del_selected_btn.clicked.connect(self._on_delete_selected)
        tb_layout.addWidget(self._del_selected_btn)
        layout.addWidget(toolbar)

        # 拖拽提示条
        self._drop_hint = QLabel("拖拽发票文件或文件夹到此处导入")
        self._drop_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._drop_hint.setStyleSheet(
            "background: #F0F7FF; color: #1E5BA8; padding: 24px; "
            "border: 2px dashed #90CAF9; border-radius: 8px; font-size: 14px;"
        )
        layout.addWidget(self._drop_hint)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll, 1)

        self._container = QWidget()
        self._list_layout = QVBoxLayout(self._container)
        self._list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._list_layout.setSpacing(6)
        self._list_layout.setContentsMargins(8, 8, 8, 8)
        scroll.setWidget(self._container)

        self._cards: dict = {}

    def set_invoices(self, invoices: List[Invoice]):
        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._cards.clear()
        self._select_all_cb.blockSignals(True)
        self._select_all_cb.setChecked(False)
        self._select_all_cb.blockSignals(False)
        self._del_selected_btn.setEnabled(False)

        self._drop_hint.setVisible(len(invoices) == 0)

        for inv in invoices:
            card = InvoiceCard(inv)
            card.clicked.connect(self.invoice_selected)
            card.delete_requested.connect(self.invoice_delete)
            card.check_changed.connect(self._on_card_check_changed)
            self._list_layout.addWidget(card)
            self._cards[inv.file_path] = card

    def _on_select_all(self, state: int):
        checked = (state == 2)
        for card in self._cards.values():
            card.set_checked(checked)
        self._update_delete_btn()

    def _on_card_check_changed(self, file_path: str, checked: bool):
        self._update_delete_btn()
        # 同步全选框状态
        all_checked = all(c.is_checked() for c in self._cards.values())
        any_checked = any(c.is_checked() for c in self._cards.values())
        self._select_all_cb.blockSignals(True)
        if all_checked:
            self._select_all_cb.setCheckState(Qt.CheckState.Checked)
        elif any_checked:
            self._select_all_cb.setCheckState(Qt.CheckState.PartiallyChecked)
        else:
            self._select_all_cb.setCheckState(Qt.CheckState.Unchecked)
        self._select_all_cb.blockSignals(False)

    def _update_delete_btn(self):
        has_selected = any(c.is_checked() for c in self._cards.values())
        self._del_selected_btn.setEnabled(has_selected)

    def _on_delete_selected(self):
        selected = [fp for fp, card in self._cards.items() if card.is_checked()]
        if selected:
            self.invoices_delete_batch.emit(selected)

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
            "background: #F0F7FF; color: #1E5BA8; padding: 24px; "
            "border: 2px dashed #90CAF9; border-radius: 8px; font-size: 14px;"
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
