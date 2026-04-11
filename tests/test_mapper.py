from core.mapper import map_baidu_response
from core.models import InvoiceStatus, InvoiceSheet

SAMPLE_RESPONSE = {
    "words_result": {
        "InvoiceType": {"words": "增值税专用发票"},
        "InvoiceCode": {"words": "044031900111"},
        "InvoiceNum": {"words": "12345678"},
        "InvoiceDate": {"words": "2024年01月15日"},
        "CommodityName": {"words": "办公用品"},
        "SellerName": {"words": "北京某公司"},
        "PurchaserName": {"words": "上海某公司"},
        "PurchaserRegisterNum": {"words": "91310000XXXXXXXX"},
        "TotalAmount": {"words": "1000.00"},
        "TaxRate": {"words": "13%"},
        "TaxAmount": {"words": "130.00"},
        "AmountInFiguers": {"words": "1130.00"},
    }
}


def test_map_basic_fields():
    inv = map_baidu_response("/tmp/a.pdf", SAMPLE_RESPONSE, confidence_threshold=0.9)
    assert inv.invoice_type == "增值税专用发票"
    assert inv.invoice_number == "12345678"
    assert inv.total_amount == 1130.00
    assert inv.sheet.value == "专票"
    assert inv.status == InvoiceStatus.OCR_DONE


def test_low_confidence_fields_empty_when_all_present():
    inv = map_baidu_response("/tmp/a.pdf", SAMPLE_RESPONSE, confidence_threshold=0.9)
    assert inv.low_confidence_fields == []
