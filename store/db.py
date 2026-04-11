import json
from datetime import datetime
from pathlib import Path
from typing import List

from peewee import (
    SqliteDatabase, Model, CharField, FloatField,
    TextField, AutoField
)

from core.models import Invoice, InvoiceStatus, InvoiceSheet

_db = SqliteDatabase(None)


class InvoiceRecord(Model):
    id = AutoField()
    file_path = CharField(unique=True)
    status = CharField()
    sheet = CharField()
    invoice_type = CharField(default="")
    invoice_code = CharField(default="")
    invoice_number = CharField(default="")
    issue_date = CharField(default="")
    goods_name = CharField(default="")
    seller_name = CharField(default="")
    buyer_name = CharField(default="")
    buyer_tax_id = CharField(default="")
    amount = FloatField(default=0.0)
    tax_rate = CharField(default="")
    tax_amount = FloatField(default=0.0)
    total_amount = FloatField(default=0.0)
    confidence = TextField(default="{}")
    low_confidence_fields = TextField(default="[]")
    batch_id = CharField(null=True)
    error_message = TextField(null=True)
    created_at = CharField(null=True)

    class Meta:
        database = _db
        table_name = "invoices"


class SettingsRecord(Model):
    key = CharField(primary_key=True)
    value = TextField()

    class Meta:
        database = _db
        table_name = "settings"


class Database:
    def __init__(self, db_path: Path):
        _db.init(str(db_path), pragmas={"journal_mode": "wal", "busy_timeout": 3000})
        _db.connect(reuse_if_open=True)
        _db.create_tables([InvoiceRecord, SettingsRecord], safe=True)
        self._migrate_schema()
        self._reset_processing_to_pending()

    def _migrate_schema(self):
        """为旧数据库补充新增列，避免 OperationalError。"""
        cursor = _db.execute_sql("PRAGMA table_info(invoices)")
        existing = {row[1] for row in cursor.fetchall()}
        if "created_at" not in existing:
            _db.execute_sql("ALTER TABLE invoices ADD COLUMN created_at VARCHAR(32)")

    def _reset_processing_to_pending(self):
        InvoiceRecord.update(status=InvoiceStatus.PENDING.value).where(
            InvoiceRecord.status == InvoiceStatus.PROCESSING.value
        ).execute()

    def save(self, inv: Invoice) -> int:
        data = self._to_dict(inv)
        try:
            record = InvoiceRecord.get(InvoiceRecord.file_path == inv.file_path)
            InvoiceRecord.update(data).where(InvoiceRecord.file_path == inv.file_path).execute()
            return record.id
        except InvoiceRecord.DoesNotExist:
            record = InvoiceRecord.create(**data)
            return record.id

    def update_status(self, file_path: str, status: InvoiceStatus):
        InvoiceRecord.update(status=status.value).where(
            InvoiceRecord.file_path == file_path
        ).execute()

    def get_all(self) -> List[Invoice]:
        return [self._to_invoice(r) for r in InvoiceRecord.select()]

    def is_duplicate(self, invoice_number: str, issue_date: str) -> bool:
        return InvoiceRecord.select().where(
            (InvoiceRecord.invoice_number == invoice_number) &
            (InvoiceRecord.issue_date == issue_date)
        ).exists()

    def get_setting(self, key: str, default: str = "") -> str:
        try:
            return SettingsRecord.get(SettingsRecord.key == key).value
        except SettingsRecord.DoesNotExist:
            return default

    def set_setting(self, key: str, value: str):
        SettingsRecord.replace(key=key, value=value).execute()

    @staticmethod
    def _to_dict(inv: Invoice) -> dict:
        return {
            "file_path": inv.file_path,
            "status": inv.status.value,
            "sheet": inv.sheet.value,
            "invoice_type": inv.invoice_type,
            "invoice_code": inv.invoice_code,
            "invoice_number": inv.invoice_number,
            "issue_date": inv.issue_date,
            "goods_name": inv.goods_name,
            "seller_name": inv.seller_name,
            "buyer_name": inv.buyer_name,
            "buyer_tax_id": inv.buyer_tax_id,
            "amount": inv.amount,
            "tax_rate": inv.tax_rate,
            "tax_amount": inv.tax_amount,
            "total_amount": inv.total_amount,
            "confidence": json.dumps(inv.confidence),
            "low_confidence_fields": json.dumps(inv.low_confidence_fields),
            "batch_id": inv.batch_id,
            "error_message": inv.error_message,
            "created_at": inv.created_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    @staticmethod
    def _to_invoice(r: InvoiceRecord) -> Invoice:
        return Invoice(
            file_path=r.file_path,
            status=InvoiceStatus(r.status),
            sheet=InvoiceSheet(r.sheet),
            invoice_type=r.invoice_type,
            invoice_code=r.invoice_code,
            invoice_number=r.invoice_number,
            issue_date=r.issue_date,
            goods_name=r.goods_name,
            seller_name=r.seller_name,
            buyer_name=r.buyer_name,
            buyer_tax_id=r.buyer_tax_id,
            amount=r.amount,
            tax_rate=r.tax_rate,
            tax_amount=r.tax_amount,
            total_amount=r.total_amount,
            confidence=json.loads(r.confidence),
            low_confidence_fields=json.loads(r.low_confidence_fields),
            batch_id=r.batch_id,
            error_message=r.error_message,
            created_at=r.created_at,
        )
