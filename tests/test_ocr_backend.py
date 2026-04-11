from unittest.mock import patch, MagicMock
from core.ocr_backend import BaiduOCRBackend, OCRError


def test_recognize_returns_dict():
    backend = BaiduOCRBackend(api_key="ak", secret_key="sk")
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"words_result": {"InvoiceType": {"words": "增值税专用发票"}}}
    mock_resp.raise_for_status = MagicMock()
    with patch("core.ocr_backend.requests.post", return_value=mock_resp):
        with patch.object(backend, "_get_access_token", return_value="fake_token"):
            result = backend.recognize(b"fake_image_bytes")
    assert "words_result" in result


def test_auth_error_raises_ocr_error():
    backend = BaiduOCRBackend(api_key="bad", secret_key="bad")
    with patch.object(backend, "_get_access_token", side_effect=Exception("auth failed")):
        try:
            backend.recognize(b"bytes")
            assert False, "should raise"
        except OCRError as e:
            assert e.error_type == "AUTH_ERROR"
