from unittest.mock import MagicMock, patch
from pathlib import Path
from core.parser import parse_file
from core.models import InvoiceStatus
from core.ocr_backend import BaiduOCRBackend

BAIDU_RESPONSE = {
    "words_result": {
        "InvoiceType": {"words": "增值税普通发票"},
        "InvoiceCode": {"words": "044031900111"},
        "InvoiceNum": {"words": "87654321"},
        "InvoiceDate": {"words": "2024年02月01日"},
        "CommodityName": {"words": "交通费"},
        "SellerName": {"words": "滴滴出行"},
        "PurchaserName": {"words": "某公司"},
        "PurchaserRegisterNum": {"words": ""},
        "TotalAmount": {"words": "50.00"},
        "TaxRate": {"words": "免税"},
        "TaxAmount": {"words": "0.00"},
        "AmountInFiguers": {"words": "50.00"},
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
