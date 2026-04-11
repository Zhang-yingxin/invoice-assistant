import time
import uuid
import threading
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QFileDialog, QMessageBox, QStackedWidget, QLabel,
    QSplitter, QDialog, QRadioButton, QDialogButtonBox
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from ui.sidebar import Sidebar
from ui.invoice_list import InvoiceList
from ui.detail_panel import DetailPanel
from ui.progress_bar import ProgressSummary
from store.db import Database
from core.models import Invoice, InvoiceStatus, InvoiceSheet
from core.parser import parse_file
from core.ocr_backend import BaiduOCRBackend


class OCRWorker(QThread):
    progress = pyqtSignal(int, int)    # current, total
    invoice_ready = pyqtSignal(object) # Invoice
    ocr_error = pyqtSignal(str, str)   # file_path, error_msg
    done = pyqtSignal()

    def __init__(self, files, backend, db, threshold, batch_id: str = ""):
        super().__init__()
        self.files = files
        self.backend = backend
        self.db = db
        self.threshold = threshold
        self.batch_id = batch_id
        self.cancelled = False

    def run(self):
        min_interval = 0.5  # QPS=2，两次请求最小间隔 0.5s
        last_request_time = 0.0
        for i, fp in enumerate(self.files, 1):
            if self.cancelled:
                break
            self.progress.emit(i, len(self.files))
            elapsed = time.time() - last_request_time
            if elapsed < min_interval:
                time.sleep(min_interval - elapsed)
            try:
                last_request_time = time.time()
                inv = parse_file(fp, self.backend, self.threshold)
                inv.batch_id = self.batch_id
                if inv.invoice_number and self.db.is_duplicate(inv.invoice_number, inv.issue_date):
                    inv.error_message = "DUPLICATE:该发票曾于历史批次处理过"
                self.db.save(inv)
                self.invoice_ready.emit(inv)
            except Exception as e:
                last_request_time = time.time()
                self.ocr_error.emit(str(fp), str(e))
        self.done.emit()


class MainWindow(QMainWindow):
    def __init__(self, db: Database):
        super().__init__()
        self._db = db
        self._worker = None
        self._ocr_errors = []
        self._current_batch_id: str = ""
        self.setWindowTitle("IA")
        self.resize(1200, 800)
        self.setMinimumSize(800, 500)

        central = QWidget()
        self.setCentralWidget(central)
        h_layout = QHBoxLayout(central)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(0)

        # 侧边栏
        self._sidebar = Sidebar()
        self._sidebar.nav_changed.connect(self._on_nav)
        h_layout.addWidget(self._sidebar)

        # 右侧主区域
        right = QWidget()
        v_layout = QVBoxLayout(right)
        v_layout.setContentsMargins(0, 0, 0, 0)
        v_layout.setSpacing(0)

        # 崩溃恢复提示条（如有未完成工作）
        invoices = db.get_all()
        recovering = [i for i in invoices if i.status in (
            InvoiceStatus.PENDING, InvoiceStatus.OCR_DONE, InvoiceStatus.MANUAL_EDITING
        )]
        self._banner_widget = QWidget()
        self._banner_widget.setStyleSheet(
            "background: #FFF3CD; border-bottom: 1px solid #FFD54F;"
        )
        bl = QHBoxLayout(self._banner_widget)
        bl.setContentsMargins(12, 6, 12, 6)
        lbl = QLabel(
            f"⚠ 检测到上次未完成的工作，已为您恢复 {len(recovering)} 张发票的处理状态。"
        )
        lbl.setStyleSheet("color: #5D4037; font-weight: bold;")
        bl.addWidget(lbl)
        clear_btn = QPushButton("清除并重新开始")
        clear_btn.setStyleSheet(
            "QPushButton { color: #fff; background: #E65100; border: none; "
            "border-radius: 3px; padding: 3px 10px; font-weight: bold; }"
            "QPushButton:hover { background: #BF360C; }"
        )
        clear_btn.clicked.connect(self._clear_all)
        bl.addWidget(clear_btn)
        dismiss_btn = QPushButton("取消")
        dismiss_btn.setStyleSheet(
            "QPushButton { color: #5D4037; background: transparent; border: 1px solid #5D4037; "
            "border-radius: 3px; padding: 3px 10px; font-weight: bold; }"
            "QPushButton:hover { background: #FFE0B2; }"
        )
        dismiss_btn.clicked.connect(self._banner_widget.hide)
        bl.addWidget(dismiss_btn)
        self._banner_widget.setVisible(bool(recovering))
        v_layout.addWidget(self._banner_widget)

        # 进度摘要栏 + 导出按钮
        summary_bar = QWidget()
        sb_layout = QHBoxLayout(summary_bar)
        sb_layout.setContentsMargins(4, 4, 4, 4)
        self._progress = ProgressSummary()
        self._progress.bulk_confirm_clicked.connect(self._on_bulk_confirm)
        self._progress.cancel_clicked.connect(self._on_cancel)
        sb_layout.addWidget(self._progress, 1)
        export_btn = QPushButton("导出 Excel")
        export_btn.clicked.connect(self._on_export)
        sb_layout.addWidget(export_btn)
        v_layout.addWidget(summary_bar)

        # 内容区（发票列表页 + 设置页，用 QStackedWidget 切换）
        self._stack = QStackedWidget()

        inv_page = QWidget()
        inv_layout = QHBoxLayout(inv_page)
        inv_layout.setContentsMargins(0, 0, 0, 0)
        inv_layout.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(6)
        splitter.setStyleSheet(
            "QSplitter::handle { background: #E0E0E0; }"
            "QSplitter::handle:hover { background: #1E5BA8; }"
        )

        self._inv_list = InvoiceList()
        self._inv_list.invoice_selected.connect(self._on_invoice_selected)
        self._inv_list.files_dropped.connect(self._start_ocr)
        self._inv_list.invoice_delete.connect(self._on_delete_invoice)
        self._inv_list.invoices_delete_batch.connect(self._on_delete_batch)
        self._inv_list.confirm_selected.connect(self._on_confirm_selected)
        self._inv_list.reocr_selected.connect(self._on_reocr_selected)
        self._inv_list.setMinimumWidth(260)
        splitter.addWidget(self._inv_list)

        self._detail = DetailPanel()
        self._detail.confirmed.connect(self._on_confirm_invoice_obj)
        self._detail.manual_requested.connect(self._on_manual_requested)
        self._detail.setMinimumWidth(400)
        splitter.addWidget(self._detail)

        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)

        inv_layout.addWidget(splitter)
        self._stack.addWidget(inv_page)      # index 0

        # 设置页占位（Task 12 实现后替换）
        self._settings_placeholder = QLabel("设置页（加载中...）")
        self._stack.addWidget(self._settings_placeholder)  # index 1

        v_layout.addWidget(self._stack, 1)
        h_layout.addWidget(right, 1)

        self._current_filter = "pending"  # 当前筛选：pending / done / failed
        self._refresh()

    def _get_backend(self):
        ak = self._db.get_setting("api_key", "")
        sk = self._db.get_setting("secret_key", "")
        return BaiduOCRBackend(ak, sk)

    def _refresh(self):
        invoices = self._db.get_all()
        confirmed = sum(1 for i in invoices if i.status in (
            InvoiceStatus.CONFIRMED, InvoiceStatus.MANUAL_DONE))
        pending = sum(1 for i in invoices if i.status in (
            InvoiceStatus.PENDING, InvoiceStatus.PROCESSING,
            InvoiceStatus.OCR_DONE, InvoiceStatus.MANUAL_EDITING))
        failed = sum(1 for i in invoices if i.status == InvoiceStatus.FAILED)
        total_amount = sum(i.total_amount for i in invoices
                           if i.status in (InvoiceStatus.CONFIRMED, InvoiceStatus.MANUAL_DONE))
        has_ocr_done = any(i.status == InvoiceStatus.OCR_DONE for i in invoices)
        self._progress.update_stats(len(invoices), confirmed, pending, failed, total_amount, has_ocr_done)
        self._sidebar.update_counts(pending, confirmed, failed)

        # 按当前筛选条件过滤展示
        f = self._current_filter
        if f == "done":
            filtered = [i for i in invoices if i.status in (
                InvoiceStatus.CONFIRMED, InvoiceStatus.MANUAL_DONE)]
        elif f == "failed":
            filtered = [i for i in invoices if i.status == InvoiceStatus.FAILED]
        else:  # pending（默认）
            filtered = [i for i in invoices if i.status in (
                InvoiceStatus.PENDING, InvoiceStatus.PROCESSING,
                InvoiceStatus.OCR_DONE, InvoiceStatus.MANUAL_EDITING)]
        self._inv_list.set_invoices(filtered)

    def _on_nav(self, key: str):
        if key == "import":
            self._import_files()
        elif key == "import_folder":
            self._import_folder()
        elif key == "settings":
            self._load_settings_page()
            self._stack.setCurrentIndex(1)
        else:
            self._current_filter = key  # "pending" / "done" / "failed"
            self._stack.setCurrentIndex(0)
            self._refresh()

    def _load_settings_page(self):
        # 懒加载设置页
        from ui.settings import SettingsPage
        if isinstance(self._stack.widget(1), SettingsPage):
            return
        settings_page = SettingsPage(self._db)
        self._stack.removeWidget(self._stack.widget(1))
        self._stack.insertWidget(1, settings_page)

    def _import_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择发票文件", "",
            "发票文件 (*.pdf *.jpg *.jpeg *.png)"
        )
        if not files:
            return
        self._start_ocr([Path(f) for f in files])

    def _import_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择发票文件夹")
        if not folder:
            return
        from ui.invoice_list import SUPPORTED_SUFFIXES
        files = [f for f in Path(folder).rglob("*")
                 if f.is_file() and f.suffix.lower() in SUPPORTED_SUFFIXES]
        if not files:
            QMessageBox.information(self, "无可用文件", "所选文件夹内没有找到 PDF/JPG/PNG 文件")
            return
        self._start_ocr(files)

    def _start_ocr(self, file_paths: list):
        if self._worker and self._worker.isRunning():
            QMessageBox.information(self, "识别中", "当前正在识别，请等待完成后再导入")
            return

        to_process = []
        for fp in file_paths:
            fp = Path(fp)
            if fp.stat().st_size > 50 * 1024 * 1024:
                QMessageBox.warning(self, "文件过大", f"{fp.name} 超过50MB，已跳过")
                continue
            to_process.append(fp)

        if not to_process:
            return

        threshold = float(self._db.get_setting("confidence_threshold", "0.9"))
        backend = self._get_backend()
        self._ocr_errors = []
        self._current_batch_id = str(uuid.uuid4())
        self._worker = OCRWorker(to_process, backend, self._db, threshold, self._current_batch_id)
        self._worker.progress.connect(lambda c, t: self._progress.show_processing(c, t))
        self._worker.invoice_ready.connect(lambda inv: self._refresh())
        self._worker.ocr_error.connect(self._on_ocr_error)
        self._worker.done.connect(self._on_ocr_done)
        self._worker.start()
        self._stack.setCurrentIndex(0)

    def _on_ocr_error(self, file_path: str, msg: str):
        inv = Invoice(
            file_path=file_path, status=InvoiceStatus.FAILED,
            sheet=InvoiceSheet.NORMAL, invoice_type="", invoice_code="",
            invoice_number="", issue_date="", goods_name="", seller_name="",
            buyer_name="", buyer_tax_id="", amount=0, tax_rate="",
            tax_amount=0, total_amount=0, error_message=msg,
        )
        self._db.save(inv)
        self._ocr_errors.append((file_path, msg))
        self._refresh()

    def _on_ocr_done(self):
        self._progress.hide_processing()
        self._refresh()
        if self._ocr_errors:
            lines = "\n".join(
                f"• {Path(fp).name}：{err}" for fp, err in self._ocr_errors
            )
            QMessageBox.warning(
                self, "部分发票识别失败",
                f"以下 {len(self._ocr_errors)} 张发票识别失败，请检查文件或 OCR 配置：\n\n{lines}"
            )

    def _on_cancel(self):
        if self._worker:
            self._worker.cancelled = True

    def _on_invoice_selected(self, file_path: str):
        invoices = self._db.get_all()
        inv = next((i for i in invoices if i.file_path == file_path), None)
        if inv:
            self._detail.load_invoice(inv)

    def _on_confirm_invoice_obj(self, inv):
        # 保存编辑后的所有字段，再更新状态
        self._db.save(inv)
        self._refresh()

    def _on_manual_requested(self, file_path: str):
        from ui.manual_form import ManualForm
        invoices = self._db.get_all()
        inv = next((i for i in invoices if i.file_path == file_path), None)
        if not inv:
            return
        form = ManualForm(inv, self)
        form.saved.connect(self._on_manual_saved)
        form.exec()

    def _on_manual_saved(self, inv: Invoice):
        self._db.save(inv)
        self._refresh()

    def _on_bulk_confirm(self):
        invoices = self._db.get_all()
        eligible_all = [i for i in invoices
                        if i.status == InvoiceStatus.OCR_DONE and not i.low_confidence_fields]
        if not eligible_all:
            QMessageBox.information(self, "批量确认", "没有可批量确认的发票")
            return

        eligible_batch = [i for i in eligible_all
                          if i.batch_id == self._current_batch_id] if self._current_batch_id else []

        dlg = QDialog(self)
        dlg.setWindowTitle("批量确认")
        dlg_layout = QVBoxLayout(dlg)
        dlg_layout.addWidget(QLabel("请选择确认范围："))

        radio_all = QRadioButton(f"全部待确认（{len(eligible_all)} 张）")
        radio_all.setChecked(True)
        dlg_layout.addWidget(radio_all)

        radio_batch = QRadioButton(f"仅本次导入（{len(eligible_batch)} 张）")
        radio_batch.setEnabled(bool(eligible_batch))
        dlg_layout.addWidget(radio_batch)

        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btn_box.button(QDialogButtonBox.StandardButton.Ok).setText("确认")
        btn_box.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        btn_box.accepted.connect(dlg.accept)
        btn_box.rejected.connect(dlg.reject)
        dlg_layout.addWidget(btn_box)

        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        targets = eligible_batch if radio_batch.isChecked() else eligible_all
        for inv in targets:
            self._db.update_status(inv.file_path, InvoiceStatus.CONFIRMED)
        self._refresh()

    def _on_delete_invoice(self, file_path: str):
        from store.db import InvoiceRecord
        InvoiceRecord.delete().where(InvoiceRecord.file_path == file_path).execute()
        self._refresh()

    def _on_delete_batch(self, file_paths: list):
        from store.db import InvoiceRecord
        reply = QMessageBox.question(
            self, "批量删除", f"确认删除选中的 {len(file_paths)} 张发票记录？此操作不可撤销。"
        )
        if reply == QMessageBox.StandardButton.Yes:
            for fp in file_paths:
                InvoiceRecord.delete().where(InvoiceRecord.file_path == fp).execute()
            self._refresh()

    def _on_reocr_selected(self, file_paths: list):
        if self._worker and self._worker.isRunning():
            QMessageBox.information(self, "识别中", "当前正在识别，请等待完成后再重试")
            return
        # 重置状态为 PENDING，再重新识别
        from store.db import InvoiceRecord
        for fp in file_paths:
            InvoiceRecord.update(
                status=InvoiceStatus.PENDING.value, error_message=""
            ).where(InvoiceRecord.file_path == fp).execute()
        self._start_ocr([Path(fp) for fp in file_paths])

    def _on_confirm_selected(self, file_paths: list):
        for fp in file_paths:
            self._db.update_status(fp, InvoiceStatus.CONFIRMED)
        self._refresh()

    def _on_export(self):
        from ui.export_summary import ExportSummaryDialog
        invoices = self._db.get_all()
        has_confirmed = any(i.status in (InvoiceStatus.CONFIRMED, InvoiceStatus.MANUAL_DONE)
                            for i in invoices)
        if not has_confirmed:
            QMessageBox.information(self, "导出 Excel", "暂无已确认的发票，请先确认发票后再导出。")
            return
        default_path = self._db.get_setting("export_path", "")
        selected_fps = self._inv_list.get_selected_file_paths()
        dlg = ExportSummaryDialog(invoices, default_path, self._current_batch_id, self,
                                  selected_file_paths=selected_fps)
        dlg.exec()

    def _clear_all(self):
        reply = QMessageBox.question(
            self, "清除数据", "确认清除所有发票记录并重新开始？此操作不可撤销。"
        )
        if reply == QMessageBox.StandardButton.Yes:
            from store.db import InvoiceRecord
            InvoiceRecord.delete().execute()
            self._banner_widget.hide()
            self._refresh()

