from core.models import Invoice, InvoiceStatus
from core.classifier import classify


def map_baidu_response(file_path: str, response: dict, confidence_threshold: float = 0.9) -> Invoice:
    """将百度 /vat_invoice 接口返回的 JSON 映射为 Invoice dataclass。

    百度增值税发票专用接口直接返回结构化字段，不返回字段级置信度，
    因此 confidence 全部设为 1.0，low_confidence_fields 为空。
    """
    wr = response.get("words_result", {})

    def get(key: str) -> str:
        """百度 /vat_invoice 接口直接返回字符串字段，不是 {words: ...} 嵌套结构。"""
        val = wr.get(key, "")
        if isinstance(val, str):
            return val
        if isinstance(val, list) and val:
            # 列表型字段（如 CommodityName）取第一行
            first = val[0]
            if isinstance(first, dict):
                return first.get("word", "")
            return str(first)
        return ""

    def get_float(key: str) -> float:
        try:
            return float(get(key).replace(",", ""))
        except ValueError:
            return 0.0

    # InvoiceTypeOrg 是百度返回的标准发票类型名称（如"电子发票(普通发票)"），
    # InvoiceType 对特殊票据会返回缩写（如"通行费电子普票"），分类时优先用 InvoiceTypeOrg。
    invoice_type = get("InvoiceTypeOrg") or get("InvoiceType")
    invoice_code = get("InvoiceCode")
    # 税率从 CommodityTaxRate 列表取第一行
    tax_rate_raw = wr.get("CommodityTaxRate", [])
    tax_rate = tax_rate_raw[0].get("word", "") if tax_rate_raw else ""

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
        tax_rate=tax_rate,
        tax_amount=get_float("TotalTax"),
        total_amount=get_float("AmountInFiguers"),
        confidence={},
        low_confidence_fields=[],
    )
