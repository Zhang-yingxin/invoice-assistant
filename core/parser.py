import re
from pathlib import Path

import pdfplumber
import fitz  # pymupdf

from core.models import Invoice, InvoiceStatus
from core.ocr_backend import OCRBackend, OCRError
from core.mapper import map_baidu_response

SUPPORTED_IMAGE = {".jpg", ".jpeg", ".png"}
SUPPORTED_PDF = {".pdf"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


def _pdf_to_image_bytes(pdf_path: Path, dpi: int = 300) -> bytes:
    doc = fitz.open(str(pdf_path))
    page = doc[0]
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=mat)
    return pix.tobytes("png")


def _try_pdfplumber_text(pdf_path: Path) -> str:
    """尝试用 pdfplumber 提取文字层，返回原始文本。"""
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            return "\n".join(p.extract_text() or "" for p in pdf.pages)
    except Exception:
        return ""


def _core_fields_present(raw_text: str) -> bool:
    """判断文字层是否包含发票号码、金额、日期的基本特征。"""
    has_number = bool(re.search(r"\d{8}", raw_text))
    has_amount = bool(re.search(r"\d+\.\d{2}", raw_text))
    has_date = bool(re.search(r"\d{4}年\d{2}月\d{2}日|\d{4}-\d{2}-\d{2}", raw_text))
    return has_number and has_amount and has_date


def parse_file(file_path: Path, ocr_backend: OCRBackend, confidence_threshold: float = 0.9) -> Invoice:
    """解析单个发票文件，返回 Invoice dataclass。"""
    suffix = file_path.suffix.lower()
    if suffix not in SUPPORTED_IMAGE | SUPPORTED_PDF:
        raise ValueError(f"不支持的文件格式: {suffix}")
    if file_path.stat().st_size > MAX_FILE_SIZE:
        raise ValueError(f"文件超过50MB限制: {file_path.name}")

    if suffix in SUPPORTED_IMAGE:
        image_bytes = file_path.read_bytes()
        response = ocr_backend.recognize(image_bytes)
        return map_baidu_response(str(file_path), response, confidence_threshold)

    # PDF 路径：先尝试文字层，核心字段缺失则降级到 OCR
    raw_text = _try_pdfplumber_text(file_path)
    if not (raw_text and _core_fields_present(raw_text)):
        image_bytes = _pdf_to_image_bytes(file_path)
    else:
        image_bytes = _pdf_to_image_bytes(file_path)  # 统一走 OCR 保证结构化

    response = ocr_backend.recognize(image_bytes)
    return map_baidu_response(str(file_path), response, confidence_threshold)
