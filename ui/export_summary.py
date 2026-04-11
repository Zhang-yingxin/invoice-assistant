from pathlib import Path
from typing import List
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QHBoxLayout,
    QPushButton, QCheckBox, QFileDialog, QMessageBox, QRadioButton, QButtonGroup
)
from core.models import Invoice, InvoiceStatus, InvoiceSheet

CONFIRMED_STATUSES = {InvoiceStatus.CONFIRMED, InvoiceStatus.MANUAL_DONE}


class ExportSummaryDialog(QDialog):
    def __init__(self, invoices: List[Invoice], default_path: str = "",
                 current_batch_id: str = "", parent=None,
                 selected_file_paths: List[str] = None):
        super().__init__(parent)
        self.setWindowTitle("导出 Excel")
        self.setMinimumWidth(420)
        self._invoices = invoices
        self._default_path = default_path
        self._current_batch_id = current_batch_id
        self._selected_file_paths = selected_file_paths or []
        layout = QVBoxLayout(self)

        # 导出范围选择
        layout.addWidget(QLabel("导出范围："))
        self._scope_group = QButtonGroup(self)
        self._rb_batch = QRadioButton("仅本次导入的发票")
        self._rb_all = QRadioButton("全部发票")
        self._rb_selected = QRadioButton(f"仅所选发票（{len(self._selected_file_paths)} 张）")
        self._rb_selected.setEnabled(bool(self._selected_file_paths))
        self._scope_group.addButton(self._rb_batch, 0)
        self._scope_group.addButton(self._rb_all, 1)
        self._scope_group.addButton(self._rb_selected, 2)

        # 默认选中逻辑
        if self._selected_file_paths:
            self._rb_selected.setChecked(True)
        elif current_batch_id:
            self._rb_batch.setChecked(True)
        else:
            self._rb_all.setChecked(True)

        layout.addWidget(self._rb_selected)
        layout.addWidget(self._rb_batch)
        layout.addWidget(self._rb_all)

        # 如果没有 batch_id（从未导入过），禁用本次导入选项
        if not current_batch_id:
            self._rb_batch.setEnabled(False)

        # 包含未确认选项（必须在 _update_stats 之前创建）
        self._include_unconfirmed = QCheckBox("包含未确认发票")
        layout.addWidget(self._include_unconfirmed)

        # 统计预览（动态刷新）
        self._stats_label = QLabel()
        layout.addWidget(self._stats_label)

        # 按钮（必须在 _update_stats 之前创建，因为 _update_stats 会调用 setEnabled）
        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        self._export_btn = QPushButton("选择保存位置并导出")
        self._export_btn.clicked.connect(self._do_export)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(self._export_btn)
        layout.addLayout(btn_layout)

        # 连接信号并初始化统计（所有控件已创建完毕）
        self._scope_group.idClicked.connect(self._update_stats)
        self._include_unconfirmed.stateChanged.connect(self._update_stats)
        self._update_stats()

    def _get_scope_invoices(self) -> List[Invoice]:
        if self._rb_selected.isChecked():
            fps = set(self._selected_file_paths)
            return [i for i in self._invoices if i.file_path in fps]
        if self._rb_batch.isChecked() and self._current_batch_id:
            return [i for i in self._invoices if i.batch_id == self._current_batch_id]
        return self._invoices

    def _update_stats(self):
        pool = self._get_scope_invoices()
        include_unc = self._include_unconfirmed.isChecked()
        if include_unc:
            to_export = pool
        else:
            to_export = [i for i in pool if i.status in CONFIRMED_STATUSES]

        special = sum(1 for i in to_export if i.sheet == InvoiceSheet.SPECIAL)
        normal = sum(1 for i in to_export if i.sheet == InvoiceSheet.NORMAL)
        misc = sum(1 for i in to_export if i.sheet == InvoiceSheet.MISC)
        total_amt = sum(i.total_amount for i in to_export)
        unconfirmed_cnt = sum(1 for i in pool if i.status not in CONFIRMED_STATUSES)

        text = f"专票 {special} 张  普票 {normal} 张  杂票 {misc} 张\n总金额 ¥{total_amt:,.2f}"
        if unconfirmed_cnt and not include_unc:
            text += f"\n（范围内还有 {unconfirmed_cnt} 张未确认，可勾选上方选项一并导出）"
        self._stats_label.setText(text)
        self._export_btn.setEnabled(bool(to_export))

    def _do_export(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "保存Excel", self._default_path, "Excel文件 (*.xlsx)"
        )
        if not path:
            return
        if not path.endswith(".xlsx"):
            path += ".xlsx"

        pool = self._get_scope_invoices()
        if self._include_unconfirmed.isChecked():
            to_export = pool
        else:
            to_export = [i for i in pool if i.status in CONFIRMED_STATUSES]

        from core.exporter import export_to_excel
        export_to_excel(to_export, Path(path))
        QMessageBox.information(self, "导出成功", f"已保存到:\n{path}")
        self.accept()
