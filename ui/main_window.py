import time
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QFileDialog, QMessageBox, QStackedWidget, QLabel
)
from PyQt6.QtCore import QThread, pyqtSignal
from ui.sidebar import Sidebar
from ui.invoice_list import InvoiceList
from ui.detail_panel import DetailPanel
from ui.progress_bar import ProgressSummary
from store.db import Database
from core.models import Invoice, InvoiceStatus, InvoiceSheet
from core.parser import parse_file
from core.ocr_backend import BaiduOCRBackend
import keyring

SERVICE_NAME = "invoice-assistant"


class OCRWorker(QThread):
    progress = pyqtSignal(int, int)    # current, total
    invoice_ready = pyqtSignal(object) # Invoice
    ocr_error = pyqtSignal(str, str)   # file_path, error_msg
    done = pyqtSignal()

    def __init__(self, files, backend, db, threshold):
        super().__init__()
        self.files = files
        self.backend = backend
        self.db = db
        self.threshold = threshold
        self.cancelled = False

    def run(self):
        for i, fp in enumerate(self.files, 1):
            if self.cancelled:
                break
            self.progress.emit(i, len(self.files))
            try:
                inv = parse_file(fp, self.backend, self.threshold)
                # 跨历史批次重复检测
                if inv.invoice_number and self.db.is_duplicate(inv.invoice_number, inv.issue_date):
                    inv.error_message = f"DUPLICATE:该发票曾于历史批次处理过"
                self.db.save(inv)
                self.invoice_ready.emit(inv)
            except Exception as e:
                self.ocr_error.emit(str(fp), str(e))
            time.sleep(0.5)  # QPS=2 限速
        self.done.emit()


class MainWindow(QMainWindow):
    def __init__(self, db: Database):
        super().__init__()
        self._db = db
        self._worker = None
        self._ocr_errors = []
        self.setWindowTitle("发票识别登记助手")
        self.resize(1200, 800)

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
        if recovering:
            banner_widget = QWidget()
            banner_widget.setStyleSheet("background: #FFF3CD;")
            bl = QHBoxLayout(banner_widget)
            bl.addWidget(QLabel(
                f"检测到上次未完成的工作，已为您恢复 {len(recovering)} 张发票的处理状态。"
            ))
            clear_btn = QPushButton("清除并重新开始")
            clear_btn.clicked.connect(self._clear_all)
            bl.addWidget(clear_btn)
            v_layout.addWidget(banner_widget)

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
        self._inv_list = InvoiceList()
        self._inv_list.invoice_selected.connect(self._on_invoice_selected)
        self._inv_list.files_dropped.connect(self._start_ocr)
        inv_layout.addWidget(self._inv_list, 1)
        self._detail = DetailPanel()
        self._detail.confirmed.connect(self._on_confirm_invoice)
        self._detail.manual_requested.connect(self._on_manual_requested)
        inv_layout.addWidget(self._detail, 1)
        self._stack.addWidget(inv_page)      # index 0

        # 设置页占位（Task 12 实现后替换）
        self._settings_placeholder = QLabel("设置页（加载中...）")
        self._stack.addWidget(self._settings_placeholder)  # index 1

        v_layout.addWidget(self._stack, 1)
        h_layout.addWidget(right, 1)

        self._refresh()

    def _get_backend(self):
        ak = keyring.get_password(SERVICE_NAME, "api_key") or ""
        sk = keyring.get_password(SERVICE_NAME, "secret_key") or ""
        return BaiduOCRBackend(ak, sk)

    def _refresh(self):
        invoices = self._db.get_all()
        self._inv_list.set_invoices(invoices)
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

    def _on_nav(self, key: str):
        if key == "import":
            self._import_files()
        elif key == "settings":
            self._load_settings_page()
            self._stack.setCurrentIndex(1)
        else:
            self._stack.setCurrentIndex(0)

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
        self._worker = OCRWorker(to_process, backend, self._db, threshold)
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

    def _on_confirm_invoice(self, file_path: str):
        self._db.update_status(file_path, InvoiceStatus.CONFIRMED)
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
        eligible = [i for i in invoices
                    if i.status == InvoiceStatus.OCR_DONE and not i.low_confidence_fields]
        if not eligible:
            QMessageBox.information(self, "批量确认", "没有可批量确认的发票")
            return
        reply = QMessageBox.question(
            self, "批量确认",
            f"共 {len(eligible)} 张高置信度发票，平均置信度 100%，确认后将标记为已完成",
        )
        if reply == QMessageBox.StandardButton.Yes:
            for inv in eligible:
                self._db.update_status(inv.file_path, InvoiceStatus.CONFIRMED)
            self._refresh()

    def _on_export(self):
        from ui.export_summary import ExportSummaryDialog
        invoices = self._db.get_all()
        default_path = self._db.get_setting("export_path", "")
        dlg = ExportSummaryDialog(invoices, default_path, self)
        dlg.exec()

    def _clear_all(self):
        reply = QMessageBox.question(
            self, "清除数据", "确认清除所有发票记录并重新开始？此操作不可撤销。"
        )
        if reply == QMessageBox.StandardButton.Yes:
            from store.db import InvoiceRecord
            InvoiceRecord.delete().execute()
            self._refresh()
