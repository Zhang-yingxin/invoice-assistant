from pathlib import Path
from typing import Optional
import fitz  # pymupdf
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QLineEdit, QDoubleSpinBox, QComboBox, QPushButton,
    QFormLayout, QScrollArea, QSizePolicy, QMessageBox,
    QDialog, QApplication
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QPixmap, QCursor
from core.models import Invoice, InvoiceSheet, InvoiceStatus

SHEET_OPTIONS = [s.value for s in InvoiceSheet]


class PreviewLabel(QLabel):
    """可点击的预览图，点击或悬停时弹出大图。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._full_pixmap: Optional[QPixmap] = None
        self._tooltip_dialog: Optional[QDialog] = None
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_full_pixmap(self, pix: Optional[QPixmap]):
        self._full_pixmap = pix
        self.setCursor(
            Qt.CursorShape.PointingHandCursor if pix else Qt.CursorShape.ArrowCursor
        )

    def mousePressEvent(self, event):
        if self._full_pixmap and not self._full_pixmap.isNull():
            self._show_large(event.globalPosition().toPoint())

    def enterEvent(self, event):
        if self._full_pixmap and not self._full_pixmap.isNull():
            self._show_large(QCursor.pos())

    def leaveEvent(self, event):
        self._close_tooltip()

    def _show_large(self, global_pos):
        if self._tooltip_dialog:
            return
        screen = QApplication.screenAt(global_pos)
        if screen is None:
            screen = QApplication.primaryScreen()
        screen_rect = screen.availableGeometry()
        max_w = int(screen_rect.width() * 0.7)
        max_h = int(screen_rect.height() * 0.8)

        scaled = self._full_pixmap.scaled(
            max_w, max_h,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

        dlg = QDialog(self.window())
        dlg.setWindowFlags(
            Qt.WindowType.ToolTip |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        dlg.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        lbl = QLabel(dlg)
        lbl.setPixmap(scaled)
        lbl.setFixedSize(scaled.size())
        dlg.setFixedSize(scaled.size())

        # 定位：优先在鼠标右侧，防止超出屏幕
        x = global_pos.x() + 16
        y = global_pos.y() - scaled.height() // 2
        if x + scaled.width() > screen_rect.right():
            x = global_pos.x() - scaled.width() - 16
        y = max(screen_rect.top(), min(y, screen_rect.bottom() - scaled.height()))
        dlg.move(x, y)
        dlg.show()
        self._tooltip_dialog = dlg

    def _close_tooltip(self):
        if self._tooltip_dialog:
            self._tooltip_dialog.close()
            self._tooltip_dialog = None


class DetailPanel(QWidget):
    confirmed = pyqtSignal(object)   # Invoice（含编辑后字段）
    manual_requested = pyqtSignal(str)  # file_path

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)

        # 左：预览
        self._preview = PreviewLabel("选择发票查看预览")
        self._preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview.setMinimumWidth(200)
        self._preview.setMinimumHeight(200)
        self._preview.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._preview.setStyleSheet("background: #f0f0f0;")
        layout.addWidget(self._preview, 1)

        # 右：表单
        right = QWidget()
        right.setMinimumWidth(320)
        right_layout = QVBoxLayout(right)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        form_widget = QWidget()
        self._form = QFormLayout(form_widget)
        self._form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        self._form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        scroll.setWidget(form_widget)
        right_layout.addWidget(scroll)

        self._fields: dict = {}
        self._current_inv: Optional[Invoice] = None
        self._editing = False  # 是否处于编辑模式

        self._sheet_combo = QComboBox()
        self._sheet_combo.addItems(SHEET_OPTIONS)
        self._sheet_combo.setEnabled(False)
        self._form.addRow("归属Sheet", self._sheet_combo)

        for field, label in [
            ("invoice_type", "发票种类"),
            ("invoice_number", "发票号码"),
            ("issue_date", "开票日期"),
            ("goods_name", "货物/服务名称"),
            ("seller_name", "销方名称"),
            ("buyer_name", "购买方名称 *"),
            ("buyer_tax_id", "购买方税号"),
            ("tax_rate", "税率"),
        ]:
            edit = QLineEdit()
            edit.setReadOnly(True)
            self._form.addRow(label, edit)
            self._fields[field] = edit

        for field, label in [
            ("amount", "金额"),
            ("tax_amount", "税额"),
            ("total_amount", "价税合计"),
        ]:
            spin = QDoubleSpinBox()
            spin.setMaximum(9_999_999.99)
            spin.setDecimals(2)
            spin.setReadOnly(True)
            spin.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
            self._form.addRow(label, spin)
            self._fields[field] = spin

        # 底部按钮区
        btn_layout = QHBoxLayout()
        self._manual_btn = QPushButton("手动填写")
        self._manual_btn.clicked.connect(self._on_manual)
        self._manual_btn.hide()
        btn_layout.addWidget(self._manual_btn)

        self._edit_btn = QPushButton("编辑")
        self._edit_btn.clicked.connect(self._on_edit)
        btn_layout.addWidget(self._edit_btn)

        self._confirm_btn = QPushButton("确认")
        self._confirm_btn.clicked.connect(self._on_confirm)
        btn_layout.addWidget(self._confirm_btn)

        right_layout.addLayout(btn_layout)
        layout.addWidget(right, 1)

    def load_invoice(self, inv: Invoice):
        self._current_inv = inv
        self._editing = False
        self._set_editable(False)

        self._sheet_combo.setCurrentText(inv.sheet.value)

        text_fields = [
            "invoice_type", "invoice_number", "issue_date",
            "goods_name", "seller_name", "buyer_name", "buyer_tax_id", "tax_rate"
        ]
        for f in text_fields:
            self._fields[f].setText(getattr(inv, f))

        for f in ["amount", "tax_amount", "total_amount"]:
            self._fields[f].setValue(getattr(inv, f))

        # 低置信度字段标红
        for f, widget in self._fields.items():
            if f in inv.low_confidence_fields:
                widget.setStyleSheet("border: 2px solid red;")
                widget.setToolTip("识别置信度低，请人工核对")
            else:
                widget.setStyleSheet("")
                widget.setToolTip("")

        can_confirm = inv.status in (InvoiceStatus.OCR_DONE, InvoiceStatus.MANUAL_EDITING)
        self._confirm_btn.setEnabled(can_confirm)
        self._edit_btn.setVisible(can_confirm)
        self._edit_btn.setText("编辑")
        self._manual_btn.setVisible(inv.status == InvoiceStatus.FAILED)

        # 预览
        self._preview.clear()
        self._preview.set_full_pixmap(None)
        suffix = Path(inv.file_path).suffix.lower()
        if suffix in (".jpg", ".jpeg", ".png"):
            pix = QPixmap(inv.file_path)
            if not pix.isNull():
                self._preview.set_full_pixmap(pix)
                self._preview.setPixmap(self._scale_pixmap(pix))
            else:
                self._preview.setText(f"图片加载失败\n{Path(inv.file_path).name}")
        elif suffix == ".pdf":
            self._load_pdf_preview(inv.file_path)
        else:
            self._preview.setText(f"不支持预览\n{Path(inv.file_path).name}")

    def _set_editable(self, editable: bool):
        self._sheet_combo.setEnabled(editable)
        for f, widget in self._fields.items():
            if isinstance(widget, QLineEdit):
                widget.setReadOnly(not editable)
            elif isinstance(widget, QDoubleSpinBox):
                widget.setReadOnly(not editable)
                widget.setButtonSymbols(
                    QDoubleSpinBox.ButtonSymbols.UpDownArrows if editable
                    else QDoubleSpinBox.ButtonSymbols.NoButtons
                )

    def _on_edit(self):
        if not self._editing:
            self._editing = True
            self._set_editable(True)
            self._edit_btn.setText("取消编辑")
        else:
            # 取消编辑，恢复原始数据
            self._editing = False
            self._set_editable(False)
            self._edit_btn.setText("编辑")
            if self._current_inv:
                self.load_invoice(self._current_inv)

    def _on_confirm(self):
        if not self._current_inv:
            return
        if self._editing:
            # 弹出提醒
            msg = QMessageBox(self)
            msg.setWindowTitle("数据已修改")
            msg.setText("您编辑后的数据与识别数据不一致，确认后将以您编辑的数据为准导出。")
            cancel_btn = msg.addButton("取消", QMessageBox.ButtonRole.RejectRole)
            ok_btn = msg.addButton("确认保存", QMessageBox.ButtonRole.AcceptRole)
            msg.exec()
            if msg.clickedButton() != ok_btn:
                return
        self.confirmed.emit(self._build_invoice())

    def _build_invoice(self) -> Invoice:
        """从表单当前值构建 Invoice 对象。"""
        inv = self._current_inv
        return Invoice(
            file_path=inv.file_path,
            status=InvoiceStatus.CONFIRMED,
            sheet=InvoiceSheet(self._sheet_combo.currentText()),
            invoice_type=self._fields["invoice_type"].text(),
            invoice_code=inv.invoice_code,  # 不在表单里，保留原值
            invoice_number=self._fields["invoice_number"].text(),
            issue_date=self._fields["issue_date"].text(),
            goods_name=self._fields["goods_name"].text(),
            seller_name=self._fields["seller_name"].text(),
            buyer_name=self._fields["buyer_name"].text(),
            buyer_tax_id=self._fields["buyer_tax_id"].text(),
            tax_rate=self._fields["tax_rate"].text(),
            amount=self._fields["amount"].value(),
            tax_amount=self._fields["tax_amount"].value(),
            total_amount=self._fields["total_amount"].value(),
            confidence=inv.confidence,
            low_confidence_fields=inv.low_confidence_fields,
            batch_id=inv.batch_id,
            error_message=inv.error_message,
            created_at=inv.created_at,
        )

    def _scale_pixmap(self, pix: QPixmap) -> QPixmap:
        """按 widget 尺寸 + devicePixelRatio 缩放，保证高 DPI 下清晰。"""
        dpr = self._preview.devicePixelRatio()
        w = max(self._preview.width(), 300)
        h = max(self._preview.height(), 400)
        scaled = pix.scaled(
            int(w * dpr), int(h * dpr),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        scaled.setDevicePixelRatio(dpr)
        return scaled

    def _load_pdf_preview(self, file_path: str):
        try:
            doc = fitz.open(file_path)
            page = doc[0]
            dpr = self._preview.devicePixelRatio()
            # 渲染分辨率 = 显示尺寸 × DPR × 基础倍数(2x)
            scale = 2.0 * dpr
            mat = fitz.Matrix(scale, scale)
            pix = page.get_pixmap(matrix=mat)
            img_bytes = pix.tobytes("png")
            qpix = QPixmap()
            qpix.loadFromData(img_bytes)
            if not qpix.isNull():
                self._preview.set_full_pixmap(qpix)
                self._preview.setPixmap(self._scale_pixmap(qpix))
            else:
                self._preview.setText(f"PDF渲染失败\n{Path(file_path).name}")
        except Exception as e:
            self._preview.setText(f"PDF预览失败\n{e}")

    def _on_manual(self):
        if self._current_inv:
            self.manual_requested.emit(self._current_inv.file_path)
