from pathlib import Path
from typing import List
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QScrollArea, QFrame,
    QHBoxLayout, QLabel, QPushButton, QCheckBox, QSizePolicy, QComboBox
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
    reocr_requested = pyqtSignal(str)   # file_path

    def __init__(self, inv: Invoice, number: int = 0, parent=None):
        super().__init__(parent)
        self.file_path = inv.file_path
        self.status = inv.status
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

        # 序号
        if number > 0:
            num_label = QLabel(f"{number}.")
            num_label.setFixedWidth(32)
            num_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            num_label.setStyleSheet("color: #999; font-size: 11px;")
            layout.addWidget(num_label)

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

        # 失败时显示重试按钮
        if inv.status == InvoiceStatus.FAILED:
            retry_btn = QPushButton("重试")
            retry_btn.setFixedHeight(22)
            retry_btn.setStyleSheet(
                "QPushButton { color: #fff; background: #FF9800; border: none; "
                "border-radius: 3px; padding: 0 8px; font-size: 11px; font-weight: bold; }"
                "QPushButton:hover { background: #F57C00; }"
            )
            retry_btn.setToolTip("重新识别此发票")
            retry_btn.clicked.connect(lambda: self.reocr_requested.emit(self.file_path))
            layout.addWidget(retry_btn)

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
    invoice_selected = pyqtSignal(str)       # file_path
    invoice_delete = pyqtSignal(str)         # file_path
    invoices_delete_batch = pyqtSignal(list) # list[str] file_paths
    files_dropped = pyqtSignal(list)         # list[Path]
    confirm_selected = pyqtSignal(list)      # list[str] file_paths
    reocr_selected = pyqtSignal(list)        # list[str] file_paths

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
        self._reocr_selected_btn = QPushButton("重新识别所选")
        self._reocr_selected_btn.setEnabled(False)
        self._reocr_selected_btn.setStyleSheet(
            "QPushButton { color: #fff; background: #FF9800; border: none; "
            "border-radius: 3px; padding: 3px 10px; font-weight: bold; }"
            "QPushButton:hover { background: #F57C00; }"
            "QPushButton:disabled { background: #E0E0E0; color: #9E9E9E; }"
        )
        self._reocr_selected_btn.clicked.connect(self._on_reocr_selected)
        tb_layout.addWidget(self._reocr_selected_btn)
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

        # 分页控制栏
        page_bar = QWidget()
        page_bar.setStyleSheet("background: #1E3A5F; border-top: 1px solid #0D2540;")
        pb_layout = QHBoxLayout(page_bar)
        pb_layout.setContentsMargins(8, 4, 8, 4)
        pb_layout.setSpacing(6)

        lbl_per = QLabel("每页")
        lbl_per.setStyleSheet("color: #fff;")
        pb_layout.addWidget(lbl_per)
        self._page_size_combo = QComboBox()
        self._page_size_combo.addItems(["10", "20", "50", "100"])
        self._page_size_combo.setCurrentText("20")
        self._page_size_combo.setFixedWidth(60)
        self._page_size_combo.setStyleSheet(
            "QComboBox { background: #2A4F7A; color: #fff; border: 1px solid #3A6FA0; "
            "border-radius: 3px; padding: 1px 4px; }"
            "QComboBox::drop-down { border: none; }"
            "QComboBox QAbstractItemView { background: #2A4F7A; color: #fff; "
            "selection-background-color: #1E5BA8; }"
        )
        self._page_size_combo.currentTextChanged.connect(self._on_page_size_changed)
        pb_layout.addWidget(self._page_size_combo)
        lbl_row = QLabel("条")
        lbl_row.setStyleSheet("color: #fff;")
        pb_layout.addWidget(lbl_row)

        pb_layout.addStretch()

        btn_style = (
            "QPushButton { border: 1px solid #3A6FA0; border-radius: 3px; "
            "padding: 0 8px; background: #2A4F7A; color: #fff; }"
            "QPushButton:hover { background: #3A6FA0; }"
            "QPushButton:disabled { color: #5A7A9A; background: #1A3050; border-color: #2A4F7A; }"
        )

        self._prev_btn = QPushButton("◀ 上一页")
        self._prev_btn.setFixedHeight(24)
        self._prev_btn.setStyleSheet(btn_style)
        self._prev_btn.clicked.connect(self._on_prev_page)
        pb_layout.addWidget(self._prev_btn)

        self._page_label = QLabel("第1页/共1页")
        self._page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._page_label.setStyleSheet("color: #fff; font-size: 12px;")
        self._page_label.setMinimumWidth(90)
        pb_layout.addWidget(self._page_label)

        self._next_btn = QPushButton("下一页 ▶")
        self._next_btn.setFixedHeight(24)
        self._next_btn.setStyleSheet(btn_style)
        self._next_btn.clicked.connect(self._on_next_page)
        pb_layout.addWidget(self._next_btn)

        layout.addWidget(page_bar)

        self._cards: dict = {}          # file_path -> InvoiceCard (current page only)
        self._all_invoices: List[Invoice] = []
        self._checked_fps: set = set()  # tracks checked state across all pages
        self._current_page: int = 0
        self._page_size: int = 20

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def set_invoices(self, invoices: List[Invoice]):
        self._all_invoices = list(invoices)
        # Remove checked items that are no longer in the list
        fps = {inv.file_path for inv in invoices}
        self._checked_fps = self._checked_fps & fps
        self._current_page = 0
        self._render_page()

    def get_selected_file_paths(self) -> list:
        return list(self._checked_fps)

    # ------------------------------------------------------------------ #
    #  Pagination internals                                                #
    # ------------------------------------------------------------------ #

    def _total_pages(self) -> int:
        if not self._all_invoices:
            return 1
        return max(1, (len(self._all_invoices) + self._page_size - 1) // self._page_size)

    def _render_page(self):
        # Clear current cards
        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._cards.clear()

        self._select_all_cb.blockSignals(True)
        self._select_all_cb.setChecked(False)
        self._select_all_cb.blockSignals(False)

        self._drop_hint.setVisible(len(self._all_invoices) == 0)

        total = len(self._all_invoices)
        start = self._current_page * self._page_size
        end = min(start + self._page_size, total)
        page_invoices = self._all_invoices[start:end]

        for idx, inv in enumerate(page_invoices):
            number = start + idx + 1  # global sequential number
            card = InvoiceCard(inv, number=number)
            card.clicked.connect(self.invoice_selected)
            card.delete_requested.connect(self.invoice_delete)
            card.check_changed.connect(self._on_card_check_changed)
            card.reocr_requested.connect(lambda fp: self.reocr_selected.emit([fp]))
            # Restore checked state
            if inv.file_path in self._checked_fps:
                card.set_checked(True)
            self._list_layout.addWidget(card)
            self._cards[inv.file_path] = card

        # Update pagination controls
        total_pages = self._total_pages()
        self._page_label.setText(f"第{self._current_page + 1}页/共{total_pages}页")
        self._prev_btn.setEnabled(self._current_page > 0)
        self._next_btn.setEnabled(self._current_page < total_pages - 1)

        self._sync_select_all_cb()
        self._update_delete_btn()

    def _on_page_size_changed(self, text: str):
        try:
            self._page_size = int(text)
        except ValueError:
            return
        self._current_page = 0
        self._render_page()

    def _on_prev_page(self):
        if self._current_page > 0:
            self._current_page -= 1
            self._render_page()

    def _on_next_page(self):
        if self._current_page < self._total_pages() - 1:
            self._current_page += 1
            self._render_page()

    # ------------------------------------------------------------------ #
    #  Selection logic                                                     #
    # ------------------------------------------------------------------ #

    def _on_select_all(self, state: int):
        checked = (state == 2)
        # Apply to current page cards
        for fp, card in self._cards.items():
            card.set_checked(checked)
            if checked:
                self._checked_fps.add(fp)
            else:
                self._checked_fps.discard(fp)
        self._update_delete_btn()

    def _on_card_check_changed(self, file_path: str, checked: bool):
        if checked:
            self._checked_fps.add(file_path)
        else:
            self._checked_fps.discard(file_path)
        self._update_delete_btn()
        self._sync_select_all_cb()

    def _sync_select_all_cb(self):
        if not self._cards:
            self._select_all_cb.blockSignals(True)
            self._select_all_cb.setCheckState(Qt.CheckState.Unchecked)
            self._select_all_cb.blockSignals(False)
            return
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
        has_selected = bool(self._checked_fps)
        has_failed_selected = any(
            inv.file_path in self._checked_fps and inv.status == InvoiceStatus.FAILED
            for inv in self._all_invoices
        )
        self._del_selected_btn.setEnabled(has_selected)
        self._confirm_selected_btn.setEnabled(has_selected)
        self._reocr_selected_btn.setEnabled(has_failed_selected)

    def _on_reocr_selected(self):
        selected = list(self._checked_fps)
        if selected:
            self.reocr_selected.emit(selected)

    def _on_confirm_selected(self):
        selected = list(self._checked_fps)
        if selected:
            self.confirm_selected.emit(selected)

    def _on_delete_selected(self):
        selected = list(self._checked_fps)
        if selected:
            self.invoices_delete_batch.emit(selected)

    # ------------------------------------------------------------------ #
    #  Drag & drop                                                         #
    # ------------------------------------------------------------------ #

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
        has_cards = bool(self._all_invoices)
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
                for f in p.rglob("*"):
                    if f.is_file() and f.suffix.lower() in SUPPORTED_SUFFIXES:
                        paths.append(f)
            elif p.is_file() and p.suffix.lower() in SUPPORTED_SUFFIXES:
                paths.append(p)
        if paths:
            self.files_dropped.emit(paths)
