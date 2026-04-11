from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class InvoiceSheet(Enum):
    SPECIAL = "专票"
    NORMAL = "普票"
    MISC = "杂票"


class InvoiceStatus(Enum):
    PENDING = "待确认"
    PROCESSING = "识别中"
    OCR_DONE = "识别完成"
    CONFIRMED = "已确认"
    FAILED = "识别失败"
    MANUAL_EDITING = "填写中"
    MANUAL_DONE = "手动录入"


@dataclass
class Invoice:
    file_path: str
    status: InvoiceStatus
    sheet: InvoiceSheet
    invoice_type: str
    invoice_code: str
    invoice_number: str
    issue_date: str
    goods_name: str
    seller_name: str
    buyer_name: str
    buyer_tax_id: str
    amount: float
    tax_rate: str
    tax_amount: float
    total_amount: float
    confidence: Dict[str, float] = field(default_factory=dict)
    low_confidence_fields: List[str] = field(default_factory=list)
    batch_id: Optional[str] = None
    error_message: Optional[str] = None
