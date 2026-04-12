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
