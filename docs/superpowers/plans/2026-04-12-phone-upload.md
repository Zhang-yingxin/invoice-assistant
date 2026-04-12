# 手机扫码批量上传 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用户点击侧边栏"手机上传"，弹出二维码，手机扫码后在浏览器选择多张发票照片上传，自动进入识别队列。

**Architecture:** App 内置一个基于标准库 `http.server` 的 HTTP 服务，运行在独立线程，监听局域网 IP:8765。手机访问后看到一个 HTML 上传页面，选图后逐张 POST 上传，文件保存到临时目录后通过 Qt 信号触发 `_start_ocr()`。

**Tech Stack:** Python `http.server`（标准库）、`qrcode>=7.4`、PyQt6 信号/槽、现有 `_start_ocr()` 流程。

---

## 文件结构

| 操作 | 文件 | 职责 |
|------|------|------|
| 新建 | `core/phone_server.py` | HTTP 服务：启停、路由、文件接收、局域网 IP 检测 |
| 新建 | `ui/phone_upload_dialog.py` | 弹窗：显示二维码、实时上传计数、完成按钮 |
| 新建 | `tests/test_phone_server.py` | PhoneServer 单元测试 |
| 修改 | `ui/sidebar.py` | 新增"手机上传"按钮 |
| 修改 | `ui/main_window.py` | `_on_nav()` 新增 `phone_upload` 分支 |
| 修改 | `requirements.txt` | 新增 `qrcode>=7.4` |

---

## Task 1: 新增 qrcode 依赖并验证安装

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: 在 requirements.txt 末尾添加依赖**

打开 `requirements.txt`，在末尾加一行：
```
qrcode>=7.4
```

- [ ] **Step 2: 安装依赖**

```bash
pip install qrcode>=7.4
```

Expected output 包含：`Successfully installed qrcode-...`

- [ ] **Step 3: 验证可导入**

```bash
python -c "import qrcode; print('ok')"
```

Expected: `ok`

- [ ] **Step 4: Commit**

```bash
git add requirements.txt
git commit -m "chore: add qrcode dependency for phone upload QR code generation"
```

---

## Task 2: 实现 PhoneServer 核心逻辑

**Files:**
- Create: `core/phone_server.py`
- Create: `tests/test_phone_server.py`

- [ ] **Step 1: 写失败测试**

新建 `tests/test_phone_server.py`：

```python
import io
import time
import threading
import urllib.request
import urllib.error
from pathlib import Path
import tempfile
from core.phone_server import PhoneServer


def test_get_local_ip_returns_string():
    from core.phone_server import _get_local_ip
    ip = _get_local_ip()
    assert isinstance(ip, str)
    assert len(ip) > 0


def test_server_starts_and_serves_index():
    with tempfile.TemporaryDirectory() as tmpdir:
        received = []
        server = PhoneServer(
            upload_dir=Path(tmpdir),
            on_file_received=lambda p: received.append(p),
        )
        server.start()
        time.sleep(0.2)
        try:
            url = f"http://127.0.0.1:{server.port}/"
            resp = urllib.request.urlopen(url, timeout=3)
            html = resp.read().decode()
            assert "invoice" in html.lower() or "发票" in html
        finally:
            server.stop()


def test_server_rejects_unsupported_extension():
    with tempfile.TemporaryDirectory() as tmpdir:
        received = []
        server = PhoneServer(
            upload_dir=Path(tmpdir),
            on_file_received=lambda p: received.append(p),
        )
        server.start()
        time.sleep(0.2)
        try:
            boundary = b"----boundary"
            body = (
                b"------boundary\r\n"
                b'Content-Disposition: form-data; name="file"; filename="test.exe"\r\n'
                b"Content-Type: application/octet-stream\r\n\r\n"
                b"data\r\n"
                b"------boundary--\r\n"
            )
            req = urllib.request.Request(
                f"http://127.0.0.1:{server.port}/upload",
                data=body,
                method="POST",
                headers={"Content-Type": "multipart/form-data; boundary=----boundary"},
            )
            try:
                urllib.request.urlopen(req, timeout=3)
                assert False, "Should have raised HTTPError"
            except urllib.error.HTTPError as e:
                assert e.code == 400
        finally:
            server.stop()


def test_server_accepts_jpg_upload():
    with tempfile.TemporaryDirectory() as tmpdir:
        received = []
        server = PhoneServer(
            upload_dir=Path(tmpdir),
            on_file_received=lambda p: received.append(p),
        )
        server.start()
        time.sleep(0.2)
        try:
            # 最小合法 JPEG（1x1 像素）
            jpeg_bytes = bytes([
                0xFF,0xD8,0xFF,0xE0,0x00,0x10,0x4A,0x46,0x49,0x46,0x00,0x01,
                0x01,0x00,0x00,0x01,0x00,0x01,0x00,0x00,0xFF,0xDB,0x00,0x43,
                0x00,0x08,0x06,0x06,0x07,0x06,0x05,0x08,0x07,0x07,0x07,0x09,
                0x09,0x08,0x0A,0x0C,0x14,0x0D,0x0C,0x0B,0x0B,0x0C,0x19,0x12,
                0x13,0x0F,0x14,0x1D,0x1A,0x1F,0x1E,0x1D,0x1A,0x1C,0x1C,0x20,
                0x24,0x2E,0x27,0x20,0x22,0x2C,0x23,0x1C,0x1C,0x28,0x37,0x29,
                0x2C,0x30,0x31,0x34,0x34,0x34,0x1F,0x27,0x39,0x3D,0x38,0x32,
                0x3C,0x2E,0x33,0x34,0x32,0xFF,0xC0,0x00,0x0B,0x08,0x00,0x01,
                0x00,0x01,0x01,0x01,0x11,0x00,0xFF,0xC4,0x00,0x1F,0x00,0x00,
                0x01,0x05,0x01,0x01,0x01,0x01,0x01,0x01,0x00,0x00,0x00,0x00,
                0x00,0x00,0x00,0x00,0x01,0x02,0x03,0x04,0x05,0x06,0x07,0x08,
                0x09,0x0A,0x0B,0xFF,0xC4,0x00,0xB5,0x10,0x00,0x02,0x01,0x03,
                0x03,0x02,0x04,0x03,0x05,0x05,0x04,0x04,0x00,0x00,0x01,0x7D,
                0xFF,0xDA,0x00,0x08,0x01,0x01,0x00,0x00,0x3F,0x00,0xFB,0xD2,
                0x8A,0x28,0x03,0xFF,0xD9,
            ])
            body = (
                b"------boundary\r\n"
                b'Content-Disposition: form-data; name="file"; filename="invoice.jpg"\r\n'
                b"Content-Type: image/jpeg\r\n\r\n"
                + jpeg_bytes +
                b"\r\n------boundary--\r\n"
            )
            req = urllib.request.Request(
                f"http://127.0.0.1:{server.port}/upload",
                data=body,
                method="POST",
                headers={"Content-Type": "multipart/form-data; boundary=----boundary"},
            )
            resp = urllib.request.urlopen(req, timeout=3)
            assert resp.status == 200
            time.sleep(0.1)
            assert len(received) == 1
            assert received[0].suffix == ".jpg"
        finally:
            server.stop()
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd /Users/zhangyingxin/Desktop/输入输出/invoice-assistant
python -m pytest tests/test_phone_server.py -v
```

Expected: `ImportError: cannot import name 'PhoneServer'`

- [ ] **Step 3: 实现 `core/phone_server.py`**

新建 `core/phone_server.py`：

```python
import io
import socket
import threading
import time
import cgi
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Callable, Optional

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

_UPLOAD_HTML = """<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>发票上传</title>
<style>
  body { font-family: -apple-system, sans-serif; max-width: 480px; margin: 0 auto;
         padding: 20px; background: #f5f5f5; }
  h2 { color: #1E5BA8; text-align: center; }
  .btn { display: block; width: 100%; padding: 14px; font-size: 16px;
         background: #1E5BA8; color: white; border: none; border-radius: 8px;
         margin: 12px 0; cursor: pointer; }
  .btn:active { background: #0D47A1; }
  #status { margin-top: 16px; color: #333; font-size: 14px; min-height: 24px; }
  #file-list { margin-top: 8px; font-size: 13px; color: #666; }
  .ok { color: #388E3C; } .err { color: #D32F2F; }
</style>
</head>
<body>
<h2>📄 发票上传</h2>
<p style="text-align:center;color:#666">选择发票照片或 PDF，支持多选</p>
<input type="file" id="picker" multiple accept="image/*,.pdf" style="display:none">
<button class="btn" onclick="document.getElementById('picker').click()">选择文件</button>
<button class="btn" id="upload-btn" style="background:#888" disabled onclick="uploadAll()">上传</button>
<div id="status"></div>
<div id="file-list"></div>
<script>
let files = [];
document.getElementById('picker').addEventListener('change', function(e) {
  files = Array.from(e.target.files);
  const list = document.getElementById('file-list');
  list.innerHTML = files.map(f => '<div>' + f.name + ' (' + (f.size/1024).toFixed(0) + ' KB)</div>').join('');
  document.getElementById('upload-btn').disabled = files.length === 0;
  document.getElementById('upload-btn').style.background = files.length > 0 ? '#1E5BA8' : '#888';
  document.getElementById('status').textContent = '已选择 ' + files.length + ' 个文件';
});
async function uploadAll() {
  const btn = document.getElementById('upload-btn');
  btn.disabled = true;
  const status = document.getElementById('status');
  let ok = 0, fail = 0;
  for (let i = 0; i < files.length; i++) {
    status.textContent = '上传中 ' + (i+1) + '/' + files.length + '：' + files[i].name;
    const fd = new FormData();
    fd.append('file', files[i]);
    try {
      const resp = await fetch('/upload', {method: 'POST', body: fd});
      if (resp.ok) { ok++; }
      else {
        const msg = await resp.text();
        fail++;
        document.getElementById('file-list').innerHTML +=
          '<div class="err">✗ ' + files[i].name + '：' + msg + '</div>';
      }
    } catch(e) {
      fail++;
      document.getElementById('file-list').innerHTML +=
        '<div class="err">✗ ' + files[i].name + '：网络错误</div>';
    }
  }
  status.innerHTML = '<span class="ok">✓ 已上传 ' + ok + ' 张</span>' +
    (fail ? '<span class="err">，' + fail + ' 张失败</span>' : '') +
    '，可继续选择新文件';
  btn.disabled = false;
  files = [];
  document.getElementById('picker').value = '';
}
</script>
</body>
</html>"""


def _get_local_ip() -> str:
    """获取局域网 IP，失败时返回 127.0.0.1。"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def _find_free_port(start: int = 8765, attempts: int = 5) -> int:
    """从 start 开始找一个可用端口。"""
    for port in range(start, start + attempts):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind(("", port))
            s.close()
            return port
        except OSError:
            continue
    raise OSError(f"无法找到可用端口（尝试了 {start}-{start+attempts-1}）")


class _Handler(BaseHTTPRequestHandler):
    """HTTP 请求处理器，持有对 PhoneServer 的引用。"""

    server: "PhoneServer"  # type: ignore[assignment]

    def log_message(self, format, *args):  # noqa: A002
        pass  # 静默日志

    def do_GET(self):
        if self.path == "/":
            body = _UPLOAD_HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path != "/upload":
            self.send_error(404)
            return

        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in content_type:
            self._respond(400, "需要 multipart/form-data")
            return

        content_length = int(self.headers.get("Content-Length", 0))
        if content_length > MAX_FILE_SIZE:
            self._respond(413, "文件过大（超过 50MB）")
            return

        environ = {
            "REQUEST_METHOD": "POST",
            "CONTENT_TYPE": content_type,
            "CONTENT_LENGTH": str(content_length),
        }
        body = self.rfile.read(content_length)
        form = cgi.FieldStorage(
            fp=io.BytesIO(body),
            environ=environ,
            keep_blank_values=True,
        )

        file_item = form.get("file")
        if not file_item or not file_item.filename:
            self._respond(400, "未找到文件字段")
            return

        filename = Path(file_item.filename).name
        suffix = Path(filename).suffix.lower()
        if suffix not in ALLOWED_EXTENSIONS:
            self._respond(400, f"不支持的格式 {suffix}，仅支持 jpg/png/pdf")
            return

        file_data = file_item.file.read()
        if len(file_data) > MAX_FILE_SIZE:
            self._respond(413, "文件过大（超过 50MB）")
            return

        # 保存到临时目录
        ts = int(time.time() * 1000)
        save_path = self.server.upload_dir / f"{ts}_{filename}"
        save_path.write_bytes(file_data)

        # 通知主线程
        self.server.on_file_received(save_path)

        self._respond(200, "ok")

    def _respond(self, code: int, message: str):
        body = message.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class PhoneServer:
    """局域网 HTTP 服务，接收手机上传的发票文件。"""

    def __init__(
        self,
        upload_dir: Path,
        on_file_received: Callable[[Path], None],
        start_port: int = 8765,
    ):
        self.upload_dir = upload_dir
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.on_file_received = on_file_received
        self.port = _find_free_port(start_port)
        self.ip = _get_local_ip()
        self.url = f"http://{self.ip}:{self.port}/"
        self._server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    def start(self):
        """启动 HTTP 服务（非阻塞）。"""
        self._server = HTTPServer(("", self.port), _Handler)
        self._server.upload_dir = self.upload_dir          # type: ignore[attr-defined]
        self._server.on_file_received = self.on_file_received  # type: ignore[attr-defined]
        self._thread = threading.Thread(
            target=self._server.serve_forever, daemon=True
        )
        self._thread.start()

    def stop(self):
        """停止 HTTP 服务。"""
        if self._server:
            self._server.shutdown()
            self._server = None
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None
```

- [ ] **Step 4: 运行测试确认通过**

```bash
python -m pytest tests/test_phone_server.py -v
```

Expected: 4 个测试全部 PASS

- [ ] **Step 5: Commit**

```bash
git add core/phone_server.py tests/test_phone_server.py
git commit -m "feat: add PhoneServer HTTP service for mobile invoice upload"
```

---

## Task 3: 实现上传对话框

**Files:**
- Create: `ui/phone_upload_dialog.py`

- [ ] **Step 1: 新建 `ui/phone_upload_dialog.py`**

```python
import shutil
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
    """手机扫码上传对话框。关闭时自动停止服务并清理临时目录。"""

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
        img = qr.make_image(fill_color="black", back_color="white")
        # 转为 QPixmap
        buf = img.tobytes()
        w, h = img.size
        qimage = QImage(buf, w, h, QImage.Format.Format_RGB888)
        return QPixmap.fromImage(qimage).scaled(
            size, size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

    def _on_file_received(self, path: Path):
        """HTTP 线程回调，更新计数（线程安全：只写列表，UI 更新用 invokeMethod）。"""
        self._uploaded.append(path)
        from PyQt6.QtCore import QMetaObject, Q_ARG
        QMetaObject.invokeMethod(
            self._count_label,
            "setText",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(str, f"已上传：{len(self._uploaded)} 张"),
        )

    def _on_done(self):
        self._server.stop()
        if self._uploaded:
            self.files_uploaded.emit(list(self._uploaded))
        self.accept()

    def closeEvent(self, event):
        self._server.stop()
        # 注意：不删除临时目录，文件还在被 OCR 使用；由调用方在识别完成后清理
        super().closeEvent(event)
```

- [ ] **Step 2: 运行现有测试确认没有破坏**

```bash
python -m pytest tests/ -v --ignore=tests/test_phone_server.py
```

Expected: 所有测试 PASS（phone_server 测试单独跑）

- [ ] **Step 3: Commit**

```bash
git add ui/phone_upload_dialog.py
git commit -m "feat: add PhoneUploadDialog with QR code display and upload counter"
```

---

## Task 4: 侧边栏新增"手机上传"入口

**Files:**
- Modify: `ui/sidebar.py`

- [ ] **Step 1: 在 sidebar.py 的按钮列表中新增 phone_upload**

找到 `__init__` 里的按钮列表，在 `("import_folder", "批量导入文件夹")` 后面加一项：

```python
for key, label in [
    ("import", "导入发票"),
    ("import_folder", "批量导入文件夹"),
    ("phone_upload", "手机扫码上传"),   # 新增这行
    ("pending", "待处理"),
    ("done", "已完成"),
    ("failed", "识别失败"),
    ("settings", "设置"),
]:
```

同时在 `_on_click` 的非导入类按钮判断里把 `phone_upload` 加入例外：

```python
if key not in ("import", "import_folder", "phone_upload"):
    for k, btn in self._btns.items():
        if k not in ("import", "import_folder", "phone_upload"):
            btn.setChecked(k == key)
```

同时更新 `nav_changed` 信号的注释：

```python
nav_changed = pyqtSignal(str)  # "import"|"import_folder"|"phone_upload"|"pending"|"done"|"failed"|"settings"
```

- [ ] **Step 2: 运行现有测试确认没有破坏**

```bash
python -m pytest tests/ -v
```

Expected: 所有测试 PASS

- [ ] **Step 3: Commit**

```bash
git add ui/sidebar.py
git commit -m "feat: add phone_upload nav item to sidebar"
```

---

## Task 5: 主窗口集成

**Files:**
- Modify: `ui/main_window.py`

- [ ] **Step 1: 在 `_on_nav()` 里新增 phone_upload 分支**

找到 `_on_nav` 方法，在 `elif key == "import_folder":` 分支后面加：

```python
elif key == "phone_upload":
    self._open_phone_upload()
```

- [ ] **Step 2: 新增 `_open_phone_upload` 方法**

在 `_import_folder` 方法之后加：

```python
def _open_phone_upload(self):
    from ui.phone_upload_dialog import PhoneUploadDialog
    dlg = PhoneUploadDialog(self)
    dlg.files_uploaded.connect(self._start_ocr)
    dlg.exec()
```

- [ ] **Step 3: 运行全量测试**

```bash
python -m pytest tests/ -v
```

Expected: 所有测试 PASS

- [ ] **Step 4: Commit**

```bash
git add ui/main_window.py
git commit -m "feat: wire phone upload dialog into main window nav"
```

---

## Task 6: 手动集成测试

- [ ] **Step 1: 启动 App**

```bash
cd /Users/zhangyingxin/Desktop/输入输出/invoice-assistant
python main.py
```

- [ ] **Step 2: 点击"手机扫码上传"**

侧边栏点击"手机扫码上传"，确认：
- 弹出对话框
- 显示二维码
- 二维码下方显示局域网地址（形如 `http://192.168.x.x:8765/`）

- [ ] **Step 3: 手机扫码测试**

手机连接同一 WiFi，扫描二维码：
- 浏览器打开上传页面
- 点"选择文件"，选择 2-3 张发票照片
- 点"上传"
- 确认 App 对话框计数增加（"已上传：N 张"）

- [ ] **Step 4: 点击"完成，开始识别"**

确认：
- 对话框关闭
- App 自动开始识别上传的图片
- 发票列表出现新条目

- [ ] **Step 5: 最终 commit**

```bash
git add .
git commit -m "feat: complete phone scan upload feature - mobile QR code batch upload"
```
