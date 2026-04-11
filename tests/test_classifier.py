from core.classifier import classify
from core.models import InvoiceSheet


def test_special_invoice():
    assert classify("增值税专用发票", "044031900111") == InvoiceSheet.SPECIAL


def test_normal_invoice():
    assert classify("增值税普通发票", "044031900111") == InvoiceSheet.NORMAL


def test_electronic_invoice():
    assert classify("电子发票（普通发票）", "033001900000") == InvoiceSheet.NORMAL


def test_misc_no_code():
    assert classify("出租车票", "") == InvoiceSheet.MISC


def test_misc_no_vat():
    assert classify("餐费收据", "") == InvoiceSheet.MISC


def test_unknown_defaults_normal():
    assert classify("", "044031900111") == InvoiceSheet.NORMAL
