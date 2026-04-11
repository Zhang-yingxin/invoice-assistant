from core.models import InvoiceSheet


def classify(invoice_type: str, invoice_code: str) -> InvoiceSheet:
    """根据发票种类和发票代码判断归属Sheet。"""
    if "专用发票" in invoice_type:
        return InvoiceSheet.SPECIAL
    if "普通发票" in invoice_type or "电子发票" in invoice_type:
        return InvoiceSheet.NORMAL
    if not invoice_code and "增值税" not in invoice_type:
        return InvoiceSheet.MISC
    return InvoiceSheet.NORMAL
