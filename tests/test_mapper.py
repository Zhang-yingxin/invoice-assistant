from core.mapper import map_baidu_response
from core.models import InvoiceStatus, InvoiceSheet

# 百度 /vat_invoice 接口实际返回格式：字段直接是字符串，列表型字段是 [{row, word}, ...]
SAMPLE_RESPONSE = {
    "words_result": {
        "InvoiceType": "增值税专用发票",
        "InvoiceCode": "044031900111",
        "InvoiceNum": "12345678",
        "InvoiceDate": "2024年01月15日",
        "CommodityName": [{"row": "1", "word": "办公用品"}],
        "SellerName": "北京某公司",
        "PurchaserName": "上海某公司",
        "PurchaserRegisterNum": "91310000XXXXXXXX",
        "TotalAmount": "1000.00",
        "CommodityTaxRate": [{"row": "1", "word": "13%"}],
        "TotalTax": "130.00",
        "AmountInFiguers": "1130.00",
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
