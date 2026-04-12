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
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def _find_free_port(start: int = 8765, attempts: int = 5) -> int:
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
    server: "PhoneServer"  # type: ignore[assignment]

    def log_message(self, format, *args):  # noqa: A002
        pass

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

        file_item = form["file"] if "file" in form else None
        if file_item is None or not file_item.filename:
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

        ts = int(time.time() * 1000)
        save_path = self.server.upload_dir / f"{ts}_{filename}"
        save_path.write_bytes(file_data)
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
        self._server = HTTPServer(("", self.port), _Handler)
        self._server.upload_dir = self.upload_dir          # type: ignore[attr-defined]
        self._server.on_file_received = self.on_file_received  # type: ignore[attr-defined]
        self._thread = threading.Thread(
            target=self._server.serve_forever, daemon=True
        )
        self._thread.start()

    def stop(self):
        if self._server:
            self._server.shutdown()
            self._server = None
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None
