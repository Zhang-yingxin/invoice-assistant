from core.models import Invoice, InvoiceStatus
from core.classifier import classify


def map_baidu_response(file_path: str, response: dict, confidence_threshold: float = 0.9) -> Invoice:
    """将百度 /vat_invoice 接口返回的 JSON 映射为 Invoice dataclass。

    百度增值税发票专用接口直接返回结构化字段，不返回字段级置信度，
    因此 confidence 全部设为 1.0，low_confidence_fields 为空。
    """
    wr = response.get("words_result", {})

    def get(key: str) -> str:
        return wr.get(key, {}).get("words", "") or ""

    def get_float(key: str) -> float:
        try:
            return float(get(key).replace(",", ""))
        except ValueError:
            return 0.0

    invoice_type = get("InvoiceType")
    invoice_code = get("InvoiceCode")

    return Invoice(
        file_path=file_path,
        status=InvoiceStatus.OCR_DONE,
        sheet=classify(invoice_type, invoice_code),
        invoice_type=invoice_type,
        invoice_code=invoice_code,
        invoice_number=get("InvoiceNum"),
        issue_date=get("InvoiceDate"),
        goods_name=get("CommodityName"),
        seller_name=get("SellerName"),
        buyer_name=get("PurchaserName"),
        buyer_tax_id=get("PurchaserRegisterNum"),
        amount=get_float("TotalAmount"),
        tax_rate=get("TaxRate"),
        tax_amount=get_float("TaxAmount"),
        total_amount=get_float("AmountInFiguers"),
        confidence={},
        low_confidence_fields=[],
    )
