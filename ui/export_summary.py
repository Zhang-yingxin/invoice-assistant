from pathlib import Path
from typing import List
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QHBoxLayout,
    QPushButton, QCheckBox, QFileDialog, QMessageBox
)
from core.models import Invoice, InvoiceStatus, InvoiceSheet


class ExportSummaryDialog(QDialog):
    def __init__(self, invoices: List[Invoice], default_path: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("导出确认")
        self.setMinimumWidth(400)
        self._invoices = invoices
        self._default_path = default_path
        layout = QVBoxLayout(self)

        confirmed = [i for i in invoices if i.status in (
            InvoiceStatus.CONFIRMED, InvoiceStatus.MANUAL_DONE)]
        unconfirmed = [i for i in invoices if i.status not in (
            InvoiceStatus.CONFIRMED, InvoiceStatus.MANUAL_DONE)]

        special = sum(1 for i in confirmed if i.sheet == InvoiceSheet.SPECIAL)
        normal = sum(1 for i in confirmed if i.sheet == InvoiceSheet.NORMAL)
        misc = sum(1 for i in confirmed if i.sheet == InvoiceSheet.MISC)
        total_amt = sum(i.total_amount for i in confirmed)

        layout.addWidget(QLabel(f"专票: {special} 张  普票: {normal} 张  杂票: {misc} 张"))
        layout.addWidget(QLabel(f"已确认总金额: ¥{total_amt:,.2f}"))

        self._include_all = None
        if unconfirmed:
            layout.addWidget(QLabel(f"⚠ 尚有 {len(unconfirmed)} 张未确认发票"))
            self._include_all = QCheckBox("包含未确认发票导出")
            layout.addWidget(self._include_all)

        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        export_btn = QPushButton("选择保存位置并导出")
        export_btn.clicked.connect(self._do_export)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(export_btn)
        layout.addLayout(btn_layout)

    def _do_export(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "保存Excel", self._default_path, "Excel文件 (*.xlsx)"
        )
        if not path:
            return
        if not path.endswith(".xlsx"):
            path += ".xlsx"

        include_all = self._include_all.isChecked() if self._include_all else False
        to_export = self._invoices if include_all else [
            i for i in self._invoices
            if i.status in (InvoiceStatus.CONFIRMED, InvoiceStatus.MANUAL_DONE)
        ]

        from core.exporter import export_to_excel
        export_to_excel(to_export, Path(path))
        QMessageBox.information(self, "导出成功", f"已保存到:\n{path}")
        self.accept()
