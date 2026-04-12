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
from PyQt6.QtGui import QPixmap, QTransform
from core.models import Invoice, InvoiceSheet, InvoiceStatus

SHEET_OPTIONS = [s.value for s in InvoiceSheet]


class PreviewLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._full_pixmap: Optional[QPixmap] = None

    def set_full_pixmap(self, pix: Optional[QPixmap]):
        self._full_pixmap = pix

    def show_large(self):
        if not self._full_pixmap or self._full_pixmap.isNull():
            return

        screen = QApplication.primaryScreen()
        screen_rect = screen.availableGeometry()
        max_w = int(screen_rect.width() * 0.85)
        max_h = int(screen_rect.height() * 0.85)

        rotation = [0]

        dlg = QDialog(self.window())
        dlg.setWindowTitle("发票预览")
        dlg.setStyleSheet("background: #1E1E1E;")
        dlg_layout = QVBoxLayout(dlg)
        dlg_layout.setContentsMargins(0, 0, 0, 8)
        dlg_layout.setSpacing(6)

        lbl = QLabel()
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet("background: #1E1E1E;")
        dlg_layout.addWidget(lbl, 1)

        def _render():
            pix = self._full_pixmap
            if rotation[0] != 0:
                pix = pix.transformed(
                    QTransform().rotate(rotation[0]),
                    Qt.TransformationMode.SmoothTransformation
                )
            scaled = pix.scaled(
                max_w, max_h - 50,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            lbl.setPixmap(scaled)
            dlg.resize(
                min(scaled.width(), max_w),
                min(scaled.height() + 50, max_h)
            )

        btn_bar = QWidget()
        btn_bar.setStyleSheet("background: #2A2A2A;")
        btn_h = QHBoxLayout(btn_bar)
        btn_h.setContentsMargins(12, 4, 12, 4)
        btn_h.setSpacing(10)

        _btn_style = (
            "QPushButton { color: #DDD; background: #3A3A3A; border: 1px solid #555; "
            "border-radius: 4px; padding: 4px 18px; font-size: 13px; }"
            "QPushButton:hover { background: #4A4A4A; color: #FFF; }"
        )
        ccw_btn = QPushButton("↺  逆时针90°")
        ccw_btn.setStyleSheet(_btn_style)
        cw_btn = QPushButton("↻  顺时针90°")
        cw_btn.setStyleSheet(_btn_style)

        def _rotate_cw():
            rotation[0] = (rotation[0] + 90) % 360
            _render()

        def _rotate_ccw():
            rotation[0] = (rotation[0] - 90) % 360
            _render()

        cw_btn.clicked.connect(_rotate_cw)
        ccw_btn.clicked.connect(_rotate_ccw)

        btn_h.addStretch()
        btn_h.addWidget(ccw_btn)
        btn_h.addWidget(cw_btn)
        btn_h.addStretch()
        dlg_layout.addWidget(btn_bar)

        _render()
        dlg.exec()


class DetailPanel(QWidget):
    confirmed = pyqtSignal(object)   # Invoice（含编辑后字段）
    manual_requested = pyqtSignal(str)  # file_path

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)

        # 左：预览区
        left_preview = QWidget()
        left_layout = QVBoxLayout(left_preview)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(4)

        self._preview = PreviewLabel("选择发票查看预览")
        self._preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview.setMinimumWidth(200)
        self._preview.setMinimumHeight(200)
        self._preview.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._preview.setStyleSheet("background: #f0f0f0;")
        left_layout.addWidget(self._preview, 1)

        self._zoom_btn = QPushButton("查看大图")
        self._zoom_btn.setFixedHeight(28)
        self._zoom_btn.setStyleSheet(
            "QPushButton { border: 1px solid #BDBDBD; border-radius: 3px; "
            "background: #fff; color: #333; padding: 0 12px; }"
            "QPushButton:hover { background: #E3F2FD; color: #1565C0; }"
        )
        self._zoom_btn.clicked.connect(self._preview.show_large)
        self._zoom_btn.hide()
        left_layout.addWidget(self._zoom_btn, 0, Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(left_preview, 1)

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
        self._zoom_btn.hide()
        suffix = Path(inv.file_path).suffix.lower()
        if suffix in (".jpg", ".jpeg", ".png"):
            pix = self._load_image_with_exif(inv.file_path)
            if pix and not pix.isNull():
                self._preview.set_full_pixmap(pix)
                self._preview.setPixmap(self._scale_pixmap(pix))
                self._zoom_btn.show()
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

    def _load_image_with_exif(self, file_path: str) -> Optional[QPixmap]:
        """加载图片并根据 EXIF 旋转信息自动修正方向。"""
        try:
            from PIL import Image, ImageOps
            import io
            img = Image.open(file_path)
            # ImageOps.exif_transpose 自动处理 EXIF Orientation 标签
            img = ImageOps.exif_transpose(img)
            if img.mode != "RGB":
                img = img.convert("RGB")
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            qpix = QPixmap()
            qpix.loadFromData(buf.getvalue())
            return qpix
        except Exception:
            # PIL 失败则回退到 QPixmap 直接加载
            return QPixmap(file_path)

    def _load_pdf_preview(self, file_path: str):
        try:
            doc = fitz.open(file_path)
            page = doc[0]
            dpr = self._preview.devicePixelRatio()
            scale = 2.0 * dpr
            # fitz 渲染时自动应用 PDF 内嵌的 page.rotation，无需手动处理
            mat = fitz.Matrix(scale, scale)
            pix = page.get_pixmap(matrix=mat)
            img_bytes = pix.tobytes("png")
            qpix = QPixmap()
            qpix.loadFromData(img_bytes)
            if not qpix.isNull():
                self._preview.set_full_pixmap(qpix)
                self._preview.setPixmap(self._scale_pixmap(qpix))
                self._zoom_btn.show()
            else:
                self._preview.setText(f"PDF渲染失败\n{Path(file_path).name}")
        except Exception as e:
            self._preview.setText(f"PDF预览失败\n{e}")

    def _on_manual(self):
        if self._current_inv:
            self.manual_requested.emit(self._current_inv.file_path)
