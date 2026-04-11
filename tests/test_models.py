from core.models import Invoice, InvoiceSheet, InvoiceStatus


def test_invoice_defaults():
    inv = Invoice(
        file_path="/tmp/a.pdf",
        status=InvoiceStatus.PENDING,
        sheet=InvoiceSheet.NORMAL,
        invoice_type="", invoice_code="", invoice_number="",
        issue_date="", goods_name="", seller_name="",
        buyer_name="", buyer_tax_id="",
        amount=0.0, tax_rate="", tax_amount=0.0, total_amount=0.0,
    )
    assert inv.confidence == {}
    assert inv.low_confidence_fields == []
    assert inv.batch_id is None
    assert inv.error_message is None


def test_invoice_sheet_values():
    assert InvoiceSheet.SPECIAL.value == "专票"
    assert InvoiceSheet.NORMAL.value == "普票"
    assert InvoiceSheet.MISC.value == "杂票"


def test_invoice_status_values():
    assert InvoiceStatus.PENDING.value == "待确认"
    assert InvoiceStatus.CONFIRMED.value == "已确认"
    assert InvoiceStatus.MANUAL_DONE.value == "手动录入"
