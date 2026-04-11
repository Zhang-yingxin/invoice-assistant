from pathlib import Path
from typing import List
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QScrollArea, QFrame,
    QHBoxLayout, QLabel, QPushButton, QCheckBox, QSizePolicy
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
    clicked = pyqtSignal(str)           # file_path
    delete_requested = pyqtSignal(str)  # file_path
    check_changed = pyqtSignal(str, bool)  # file_path, checked

    def __init__(self, inv: Invoice, parent=None):
        super().__init__(parent)
        self.file_path = inv.file_path
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)

        # 复选框
        self._checkbox = QCheckBox()
        self._checkbox.setFixedWidth(20)
        self._checkbox.stateChanged.connect(
            lambda state: self.check_changed.emit(self.file_path, state == 2)
        )
        layout.addWidget(self._checkbox)

        # 左侧：文件名 + 识别时间
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(2)
        filename = Path(inv.file_path).name
        name = QLabel(filename)
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
    confirm_selected = pyqtSignal(list)  # list[str] file_paths

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 全选/删除工具栏
        toolbar = QWidget()
        toolbar.setStyleSheet("background: #ECECEC; border-bottom: 1px solid #BDBDBD;")
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(8, 5, 8, 5)
        tb_layout.setSpacing(6)
        self._select_all_cb = QCheckBox("全选")
        self._select_all_cb.setStyleSheet("color: #212121; font-weight: bold;")
        self._select_all_cb.stateChanged.connect(self._on_select_all)
        tb_layout.addWidget(self._select_all_cb)
        tb_layout.addStretch()
        self._confirm_selected_btn = QPushButton("确认所选")
        self._confirm_selected_btn.setEnabled(False)
        self._confirm_selected_btn.setStyleSheet(
            "QPushButton { color: #fff; background: #1E5BA8; border: none; "
            "border-radius: 3px; padding: 3px 10px; font-weight: bold; }"
            "QPushButton:hover { background: #0D47A1; }"
            "QPushButton:disabled { background: #E0E0E0; color: #9E9E9E; }"
        )
        self._confirm_selected_btn.clicked.connect(self._on_confirm_selected)
        tb_layout.addWidget(self._confirm_selected_btn)
        self._del_selected_btn = QPushButton("删除所选")
        self._del_selected_btn.setEnabled(False)
        self._del_selected_btn.setStyleSheet(
            "QPushButton { color: #fff; background: #e53935; border: none; "
            "border-radius: 3px; padding: 3px 10px; font-weight: bold; }"
            "QPushButton:hover { background: #c62828; }"
            "QPushButton:disabled { background: #E0E0E0; color: #9E9E9E; }"
        )
        self._del_selected_btn.clicked.connect(self._on_delete_selected)
        tb_layout.addWidget(self._del_selected_btn)
        layout.addWidget(toolbar)

        # 拖拽提示条
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
        self._list_layout = QVBoxLayout(self._container)
        self._list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._list_layout.setSpacing(4)
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
        self._confirm_selected_btn.setEnabled(has_selected)

    def get_selected_file_paths(self) -> list:
        return [fp for fp, card in self._cards.items() if card.is_checked()]

    def _on_confirm_selected(self):
        selected = self.get_selected_file_paths()
        if selected:
            self.confirm_selected.emit(selected)

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
