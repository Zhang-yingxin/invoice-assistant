from PyQt6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QDoubleSpinBox,
    QComboBox, QPushButton, QHBoxLayout, QVBoxLayout, QLabel
)
from PyQt6.QtCore import pyqtSignal
from core.models import Invoice, InvoiceStatus, InvoiceSheet
from core.classifier import classify


class ManualForm(QDialog):
    saved = pyqtSignal(object)  # Invoice

    def __init__(self, inv: Invoice, parent=None):
        super().__init__(parent)
        self.setWindowTitle("手动填写发票信息")
        self.setMinimumWidth(480)
        self._inv = inv

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self._sheet = QComboBox()
        self._sheet.addItems([s.value for s in InvoiceSheet])
        self._sheet.setCurrentText(inv.sheet.value)
        form.addRow("归属Sheet *", self._sheet)

        self._fields = {}
        required_fields = {"buyer_name"}
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
            edit = QLineEdit(getattr(inv, field.replace(" *", "").strip()) or "")
            if field in required_fields or field == "buyer_name":
                edit.setStyleSheet("border: 2px solid red;")
            form.addRow(label, edit)
            self._fields[field] = edit

        self._amount = QDoubleSpinBox()
        self._amount.setMaximum(9_999_999.99)
        self._amount.setDecimals(2)
        self._amount.setValue(inv.amount)

        self._tax_amount = QDoubleSpinBox()
        self._tax_amount.setMaximum(9_999_999.99)
        self._tax_amount.setDecimals(2)
        self._tax_amount.setValue(inv.tax_amount)

        self._total_amount = QDoubleSpinBox()
        self._total_amount.setMaximum(9_999_999.99)
        self._total_amount.setDecimals(2)
        self._total_amount.setValue(inv.total_amount)

        form.addRow("金额", self._amount)
        form.addRow("税额", self._tax_amount)
        form.addRow("价税合计 *", self._total_amount)
        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        later_btn = QPushButton("稍后继续")
        later_btn.clicked.connect(self._save_partial)
        save_btn = QPushButton("保存并完成")
        save_btn.clicked.connect(self._save)
        btn_layout.addWidget(later_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

    def _build_invoice(self, status: InvoiceStatus) -> Invoice:
        inv_type = self._fields["invoice_type"].text()
        inv_code = self._fields["invoice_code"].text()
        return Invoice(
            file_path=self._inv.file_path,
            status=status,
            sheet=InvoiceSheet(self._sheet.currentText()),
            invoice_type=inv_type,
            invoice_code=inv_code,
            invoice_number=self._fields["invoice_number"].text(),
            issue_date=self._fields["issue_date"].text(),
            goods_name=self._fields["goods_name"].text(),
            seller_name=self._fields["seller_name"].text(),
            buyer_name=self._fields["buyer_name"].text(),
            buyer_tax_id=self._fields["buyer_tax_id"].text(),
            amount=self._amount.value(),
            tax_rate=self._fields["tax_rate"].text(),
            tax_amount=self._tax_amount.value(),
            total_amount=self._total_amount.value(),
        )

    def _save(self):
        self.saved.emit(self._build_invoice(InvoiceStatus.MANUAL_DONE))
        self.accept()

    def _save_partial(self):
        self.saved.emit(self._build_invoice(InvoiceStatus.MANUAL_EDITING))
        self.accept()
