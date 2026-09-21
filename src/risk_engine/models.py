from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Invoice:
    vendor_id: Any
    vendor_name: str
    raw: dict[str, Any]
    id: Any
    tranid: str
    transactionnumber: str
    trandate: str | None
    due_date: str | None
    total: float
    amount: float
    currency: str
    memo: str | None
    reference_number: str | None
    reference_text: str | None
    bank_account: str | None
    line_items: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class VendorHistory:
    invoices: list[Invoice]

    @property
    def amounts(self) -> list[float]:
        return [invoice.amount for invoice in self.invoices if invoice.amount > 0]

    @property
    def currencies(self) -> set[str]:
        return {invoice.currency for invoice in self.invoices if invoice.currency}

    @property
    def bank_accounts(self) -> set[str]:
        return {invoice.bank_account for invoice in self.invoices if invoice.bank_account}

    @property
    def invoice_numbers(self) -> set[str]:
        values: set[str] = set()
        for invoice in self.invoices:
            values.add(invoice.tranid)
            number = invoice.raw.get("number")
            if number is not None:
                values.add(str(number))
        return values


@dataclass
class RiskFinding:
    code: str
    title: str
    detail: str
    score: int
    fields: list[str] = field(default_factory=list)


@dataclass
class RiskAssessment:
    invoice: Invoice
    risk_score: int
    risk_level: str
    findings: list[RiskFinding]
    missing_fields: list[str]
    suggested_checks: list[str]
    route_to_review: bool
    auto_approval_candidate: bool
