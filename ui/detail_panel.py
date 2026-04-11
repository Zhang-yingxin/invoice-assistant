from pathlib import Path
from typing import Optional
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QLineEdit, QDoubleSpinBox, QComboBox, QPushButton,
    QFormLayout, QScrollArea
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QPixmap
from core.models import Invoice, InvoiceSheet, InvoiceStatus

SHEET_OPTIONS = [s.value for s in InvoiceSheet]


class DetailPanel(QWidget):
    confirmed = pyqtSignal(str)    # file_path
    manual_requested = pyqtSignal(str)  # file_path（识别失败时请求手动填写）

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)

        # 左：预览
        self._preview = QLabel("选择发票查看预览")
        self._preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview.setMinimumWidth(400)
        self._preview.setStyleSheet("background: #f0f0f0;")
        layout.addWidget(self._preview, 1)

        # 右：表单
        right = QWidget()
        right_layout = QVBoxLayout(right)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        form_widget = QWidget()
        self._form = QFormLayout(form_widget)
        scroll.setWidget(form_widget)
        right_layout.addWidget(scroll)

        self._fields: dict = {}
        self._current_inv: Optional[Invoice] = None

        self._sheet_combo = QComboBox()
        self._sheet_combo.addItems(SHEET_OPTIONS)
        self._form.addRow("归属Sheet", self._sheet_combo)

        for field, label in [
            ("invoice_type", "发票种类"),
            ("invoice_code", "发票代码"),
            ("invoice_number", "发票号码"),
            ("issue_date", "开票日期"),
            ("goods_name", "货物/服务名称"),
            ("seller_name", "销方名称"),
            ("buyer_name", "购买方名称 *"),
            ("buyer_tax_id", "购买方税号"),
            ("tax_rate", "税率"),
        ]:
            edit = QLineEdit()
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
            self._form.addRow(label, spin)
            self._fields[field] = spin

        btn_layout = QHBoxLayout()
        self._confirm_btn = QPushButton("确认")
        self._confirm_btn.clicked.connect(self._on_confirm)
        self._manual_btn = QPushButton("手动填写")
        self._manual_btn.clicked.connect(self._on_manual)
        self._manual_btn.hide()
        btn_layout.addWidget(self._manual_btn)
        btn_layout.addWidget(self._confirm_btn)
        right_layout.addLayout(btn_layout)

        layout.addWidget(right, 1)

    def load_invoice(self, inv: Invoice):
        self._current_inv = inv
        self._sheet_combo.setCurrentText(inv.sheet.value)

        text_fields = [
            "invoice_type", "invoice_code", "invoice_number", "issue_date",
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

        self._confirm_btn.setEnabled(
            inv.status in (InvoiceStatus.OCR_DONE, InvoiceStatus.MANUAL_EDITING)
        )
        self._manual_btn.setVisible(inv.status == InvoiceStatus.FAILED)

        # 预览
        suffix = Path(inv.file_path).suffix.lower()
        if suffix in (".jpg", ".jpeg", ".png"):
            pix = QPixmap(inv.file_path)
            if not pix.isNull():
                self._preview.setPixmap(
                    pix.scaled(400, 600, Qt.AspectRatioMode.KeepAspectRatio,
                               Qt.TransformationMode.SmoothTransformation)
                )
            else:
                self._preview.setText(f"图片加载失败\n{Path(inv.file_path).name}")
        elif suffix == ".pdf":
            self._load_pdf_preview(inv.file_path)
        else:
            self._preview.setText(f"不支持预览\n{Path(inv.file_path).name}")

    def _load_pdf_preview(self, file_path: str):
        try:
            import fitz
            doc = fitz.open(file_path)
            page = doc[0]
            mat = fitz.Matrix(2.0, 2.0)  # 2x 缩放，清晰度够用
            pix = page.get_pixmap(matrix=mat)
            img_bytes = pix.tobytes("png")
            qpix = QPixmap()
            qpix.loadFromData(img_bytes)
            if not qpix.isNull():
                self._preview.setPixmap(
                    qpix.scaled(400, 600, Qt.AspectRatioMode.KeepAspectRatio,
                                Qt.TransformationMode.SmoothTransformation)
                )
            else:
                self._preview.setText(f"PDF渲染失败\n{Path(file_path).name}")
        except Exception as e:
            self._preview.setText(f"PDF预览失败\n{e}")

    def _on_confirm(self):
        if self._current_inv:
            self.confirmed.emit(self._current_inv.file_path)

    def _on_manual(self):
        if self._current_inv:
            self.manual_requested.emit(self._current_inv.file_path)
