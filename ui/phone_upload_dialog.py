import tempfile
from pathlib import Path

import qrcode
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
)

from core.phone_server import PhoneServer


class PhoneUploadDialog(QDialog):
    """手机扫码上传对话框。关闭时自动停止服务。"""

    files_uploaded = pyqtSignal(list)  # list[Path]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("手机扫码上传发票")
        self.setMinimumWidth(320)
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint
        )

        self._tmp_dir = Path(tempfile.mkdtemp(prefix="ia_phone_"))
        self._uploaded: list[Path] = []
        self._emitted = False

        self._server = PhoneServer(
            upload_dir=self._tmp_dir,
            on_file_received=self._on_file_received,
        )
        self._server.start()

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # 二维码
        qr_label = QLabel()
        qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        qr_img = self._make_qr_pixmap(self._server.url, size=220)
        qr_label.setPixmap(qr_img)
        layout.addWidget(qr_label)

        # 地址文字
        url_label = QLabel(self._server.url)
        url_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        url_label.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(url_label)

        # 提示
        hint = QLabel("同一 WiFi 下，用手机扫码\n选择发票照片批量上传")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet("color: #333; font-size: 13px;")
        layout.addWidget(hint)

        # 上传计数
        self._count_label = QLabel("已上传：0 张")
        self._count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._count_label.setStyleSheet(
            "color: #1E5BA8; font-size: 15px; font-weight: bold;"
        )
        layout.addWidget(self._count_label)

        # 按钮
        btn_row = QHBoxLayout()
        done_btn = QPushButton("完成，开始识别")
        done_btn.setStyleSheet(
            "QPushButton { background: #1E5BA8; color: white; border: none; "
            "border-radius: 4px; padding: 8px 20px; font-size: 14px; }"
            "QPushButton:hover { background: #0D47A1; }"
        )
        done_btn.clicked.connect(self._on_done)
        btn_row.addStretch()
        btn_row.addWidget(done_btn)
        layout.addLayout(btn_row)

    def _make_qr_pixmap(self, url: str, size: int = 220) -> QPixmap:
        qr = qrcode.QRCode(box_size=6, border=2)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
        buf = img.tobytes()
        w, h = img.size
        qimage = QImage(buf, w, h, w * 3, QImage.Format.Format_RGB888)
        return QPixmap.fromImage(qimage).scaled(
            size, size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

    def _on_file_received(self, path: Path):
        """HTTP 线程回调 — 线程安全：用 QMetaObject.invokeMethod 更新 UI。"""
        self._uploaded.append(path)
        from PyQt6.QtCore import QMetaObject, Q_ARG
        QMetaObject.invokeMethod(
            self._count_label,
            "setText",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(str, f"已上传：{len(self._uploaded)} 张"),
        )

    def _on_done(self):
        paths = list(self._uploaded)   # 先快照
        self._server.stop()            # 再停服务
        if paths:
            self._emitted = True
            self.files_uploaded.emit(paths)
        self.accept()

    def closeEvent(self, event):
        self._server.stop()
        if not self._emitted and self._tmp_dir.exists():
            import shutil
            shutil.rmtree(self._tmp_dir, ignore_errors=True)
        super().closeEvent(event)
