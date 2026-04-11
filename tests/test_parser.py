from unittest.mock import MagicMock, patch
from pathlib import Path
from core.parser import parse_file
from core.models import InvoiceStatus
from core.ocr_backend import BaiduOCRBackend

BAIDU_RESPONSE = {
    "words_result": {
        "InvoiceType": "增值税普通发票",
        "InvoiceCode": "044031900111",
        "InvoiceNum": "87654321",
        "InvoiceDate": "2024年02月01日",
        "CommodityName": [{"row": "1", "word": "交通费"}],
        "SellerName": "滴滴出行",
        "PurchaserName": "某公司",
        "PurchaserRegisterNum": "",
        "TotalAmount": "50.00",
        "CommodityTaxRate": [{"row": "1", "word": "免税"}],
        "TotalTax": "0.00",
        "AmountInFiguers": "50.00",
    }
}


def test_parse_image_file(tmp_path):
    img_file = tmp_path / "test.jpg"
    img_file.write_bytes(b"fake_image_data")
    mock_backend = MagicMock(spec=BaiduOCRBackend)
    mock_backend.recognize.return_value = BAIDU_RESPONSE
    inv = parse_file(img_file, mock_backend)
    assert inv.invoice_number == "87654321"
    assert inv.status == InvoiceStatus.OCR_DONE
    mock_backend.recognize.assert_called_once()


def test_parse_unsupported_format_raises(tmp_path):
    bad_file = tmp_path / "test.docx"
    bad_file.write_bytes(b"data")
    mock_backend = MagicMock()
    try:
        parse_file(bad_file, mock_backend)
        assert False, "should raise"
    except ValueError as e:
        assert "不支持" in str(e)
