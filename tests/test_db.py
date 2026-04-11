import tempfile
from pathlib import Path
from store.db import Database
from core.models import Invoice, InvoiceStatus, InvoiceSheet


def _make_invoice(path="/tmp/a.pdf") -> Invoice:
    return Invoice(
        file_path=path, status=InvoiceStatus.PENDING,
        sheet=InvoiceSheet.NORMAL, invoice_type="增值税普通发票",
        invoice_code="044031900111", invoice_number="12345678",
        issue_date="2024年01月01日", goods_name="办公用品",
        seller_name="卖方", buyer_name="买方", buyer_tax_id="",
        amount=100.0, tax_rate="13%", tax_amount=13.0, total_amount=113.0,
    )


def test_save_and_load():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Database(Path(tmpdir) / "test.db")
        inv = _make_invoice()
        db.save(inv)
        loaded = db.get_all()
        assert len(loaded) == 1
        assert loaded[0].invoice_number == "12345678"


def test_crash_recovery_resets_processing():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = Database(db_path)
        inv = _make_invoice()
        inv.status = InvoiceStatus.PROCESSING
        db.save(inv)
        db2 = Database(db_path)  # 模拟重启
        loaded = db2.get_all()
        assert loaded[0].status == InvoiceStatus.PENDING


def test_duplicate_detection():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Database(Path(tmpdir) / "test.db")
        inv = _make_invoice()
        db.save(inv)
        assert db.is_duplicate("12345678", "2024年01月01日") is True
        assert db.is_duplicate("99999999", "2024年01月01日") is False
