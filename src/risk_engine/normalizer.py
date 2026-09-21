from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

from src.risk_engine.models import Invoice, VendorHistory


LINE_ITEM_KEYS = [
    "lines",
    "line_items",
    "invoice_lines",
    "items",
    "expense",
    "item",
]


def load_invoice_and_history(path: Path) -> tuple[Invoice, VendorHistory]:
    data = json.loads(path.read_text(encoding="utf-8"))
    vendor = data.get("vendor") or {}
    records = data.get("records") or []
    if not records:
        raise ValueError(f"No records found in {path}")

    invoices = [invoice_from_record(vendor, record) for record in records]
    invoices.sort(key=lambda invoice: (parse_netsuite_date(invoice.trandate) or date.min, invoice.id or 0))
    return invoices[-1], VendorHistory(invoices[:-1])


def invoice_from_record(vendor: dict[str, Any], record: dict[str, Any]) -> Invoice:
    total = safe_float(record.get("total") or record.get("custbody_gs_inv_total_sum"))
    return Invoice(
        vendor_id=vendor.get("id"),
        vendor_name=str(vendor.get("name") or "Unknown vendor"),
        raw=record,
        id=record.get("id"),
        tranid=str(record.get("tranid") or record.get("number") or "unknown"),
        transactionnumber=str(record.get("transactionnumber") or ""),
        trandate=as_optional_str(record.get("trandate")),
        due_date=as_optional_str(record.get("duedate")),
        total=total,
        amount=abs(total),
        currency=str(record.get("currency") or "unknown"),
        memo=as_optional_str(record.get("memo")),
        reference_number=as_optional_str(record.get("custbody_gs_inv_reference_num")),
        reference_text=as_optional_str(record.get("custbody_gs_inv_reference_text")),
        bank_account=as_optional_str(record.get("custbody_gs_invoicing_bank_account")),
        line_items=extract_line_items(record),
    )


def safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def as_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def extract_line_items(record: dict[str, Any]) -> list[dict[str, Any]]:
    for key in LINE_ITEM_KEYS:
        value = record.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def parse_netsuite_date(value: str | None) -> date | None:
    if not value:
        return None
    for pattern in ("%d.%m.%Y", "%d/%m/%Y %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, pattern).date()
        except ValueError:
            continue
    return None
