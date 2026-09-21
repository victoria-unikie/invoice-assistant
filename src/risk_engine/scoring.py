from __future__ import annotations

import os
from datetime import date, timedelta
from statistics import mean

from src.risk_engine.models import Invoice, RiskAssessment, RiskFinding, VendorHistory
from src.risk_engine.normalizer import LINE_ITEM_KEYS, parse_netsuite_date


REQUIRED_REFERENCE_FIELDS = [
    "custbody_gs_inv_reference_num",
    "custbody_gs_inv_reference_text",
    "custbody_gs_invoicing_bank_account",
    "duedate",
    "trandate",
    "total",
    "currency",
]


def assess_invoice(invoice: Invoice, history: VendorHistory, today: date) -> RiskAssessment:
    findings: list[RiskFinding] = []
    missing_fields = missing_reference_fields(invoice.raw)
    suggested_checks: list[str] = []
    unknown_reasons: list[str] = []

    for field_name in missing_fields:
        findings.append(
            RiskFinding(
                code="missing_required_field",
                title=f"Missing {field_name}",
                detail=f"The NetSuite field {field_name} is empty on this bill.",
                score=field_score(field_name),
                fields=[field_name],
            )
        )

    if not history.invoices:
        unknown_reasons.append("no previous vendor history is available")
        findings.append(
            RiskFinding(
                code="no_vendor_history",
                title="No vendor history",
                detail="Risk is unknown because no previous vendor history is available.",
                score=35,
            )
        )
        suggested_checks.append("Confirm the vendor, payment details, and expected amount before approval.")
    else:
        add_amount_findings(invoice, history, findings, suggested_checks)
        add_currency_findings(invoice, history, findings, suggested_checks)
        add_payment_findings(invoice, history, findings, suggested_checks)
        add_duplicate_findings(invoice, history, findings, suggested_checks)

    add_due_date_findings(invoice, today, findings, suggested_checks)

    if not invoice.line_items:
        unknown_reasons.append("line item details are not present in this export")
        findings.append(
            RiskFinding(
                code="line_items_unavailable",
                title="Line item comparison unavailable",
                detail=(
                    "Line item details are not present in this export, so description, "
                    "quantity, unit price, and tax comparison could not be checked."
                ),
                score=0,
                fields=LINE_ITEM_KEYS,
            )
        )
        suggested_checks.append("Review the source document or NetSuite bill lines before approving.")

    score = min(100, sum(finding.score for finding in findings))
    risk_level = "unknown" if unknown_reasons else classify_score(score)
    route_to_review = risk_level in {"medium", "high", "unknown"}
    auto_approval_enabled = os.getenv("ENABLE_AUTO_APPROVAL", "false").lower() == "true"
    auto_approval_candidate = (
        auto_approval_enabled
        and risk_level == "low"
        and bool(history.invoices)
        and not missing_fields
        and not invoice_has_code(findings, "possible_duplicate")
        and not invoice_has_code(findings, "changed_bank_account")
    )

    if not suggested_checks:
        suggested_checks.append("Confirm this matches the expected recurring invoice before approval.")

    return RiskAssessment(
        invoice=invoice,
        risk_score=score,
        risk_level=risk_level,
        findings=findings,
        missing_fields=missing_fields,
        suggested_checks=dedupe(suggested_checks),
        route_to_review=route_to_review,
        auto_approval_candidate=auto_approval_candidate,
    )


def classify_score(score: int) -> str:
    if score <= 20:
        return "low"
    if score <= 50:
        return "medium"
    return "high"


def missing_reference_fields(record: dict[str, object]) -> list[str]:
    missing: list[str] = []
    for field_name in REQUIRED_REFERENCE_FIELDS:
        if record.get(field_name) in (None, ""):
            missing.append(field_name)
    return missing


def field_score(field_name: str) -> int:
    if field_name == "custbody_gs_inv_reference_num":
        return 15
    if field_name == "custbody_gs_invoicing_bank_account":
        return 20
    return 10


def add_amount_findings(
    invoice: Invoice,
    history: VendorHistory,
    findings: list[RiskFinding],
    suggested_checks: list[str],
) -> None:
    historical_amounts = history.amounts
    if not historical_amounts:
        findings.append(
            RiskFinding(
                code="amount_history_missing",
                title="No amount history",
                detail="Historical invoice amounts were unavailable for comparison.",
                score=10,
                fields=["total", "custbody_gs_inv_total_sum"],
            )
        )
        return

    average_amount = mean(historical_amounts)
    if average_amount <= 0:
        return

    change_ratio = (invoice.amount - average_amount) / average_amount
    if change_ratio > 0.50:
        findings.append(
            RiskFinding(
                code="amount_spike_high",
                title="Amount is more than 50% above average",
                detail=(
                    f"Current amount {format_money(invoice.amount)} is {change_ratio:.0%} "
                    f"above the vendor average {format_money(average_amount)}."
                ),
                score=45,
                fields=["total", "custbody_gs_inv_total_sum"],
            )
        )
        suggested_checks.append("Confirm the amount against contract, PO, or recurring rent schedule.")
    elif change_ratio > 0.20:
        findings.append(
            RiskFinding(
                code="amount_spike_medium",
                title="Amount is 20-50% above average",
                detail=(
                    f"Current amount {format_money(invoice.amount)} is {change_ratio:.0%} "
                    f"above the vendor average {format_money(average_amount)}."
                ),
                score=25,
                fields=["total", "custbody_gs_inv_total_sum"],
            )
        )
        suggested_checks.append("Confirm the amount change is expected.")


def add_currency_findings(
    invoice: Invoice,
    history: VendorHistory,
    findings: list[RiskFinding],
    suggested_checks: list[str],
) -> None:
    if invoice.currency not in history.currencies:
        findings.append(
            RiskFinding(
                code="new_currency",
                title="New currency for vendor",
                detail=f"Currency {invoice.currency} has not appeared in this vendor history.",
                score=30,
                fields=["currency"],
            )
        )
        suggested_checks.append("Confirm currency and tax handling before approval.")


def add_payment_findings(
    invoice: Invoice,
    history: VendorHistory,
    findings: list[RiskFinding],
    suggested_checks: list[str],
) -> None:
    if not invoice.bank_account:
        return
    if history.bank_accounts and invoice.bank_account not in history.bank_accounts:
        findings.append(
            RiskFinding(
                code="changed_bank_account",
                title="Payment details require confirmation",
                detail=(
                    "The value in custbody_gs_invoicing_bank_account differs from previous "
                    "bills for this vendor."
                ),
                score=60,
                fields=["custbody_gs_invoicing_bank_account"],
            )
        )
        suggested_checks.append("Confirm payment details through the normal finance control.")


def add_duplicate_findings(
    invoice: Invoice,
    history: VendorHistory,
    findings: list[RiskFinding],
    suggested_checks: list[str],
) -> None:
    invoice_numbers = {invoice.tranid}
    if invoice.raw.get("number") is not None:
        invoice_numbers.add(str(invoice.raw.get("number")))

    if invoice_numbers & history.invoice_numbers:
        findings.append(
            RiskFinding(
                code="possible_duplicate",
                title="Possible duplicate invoice number",
                detail="The invoice number already appears in this vendor history.",
                score=50,
                fields=["tranid", "number"],
            )
        )
        suggested_checks.append("Check whether this invoice has already been processed.")


def add_due_date_findings(
    invoice: Invoice,
    today: date,
    findings: list[RiskFinding],
    suggested_checks: list[str],
) -> None:
    due_date = parse_netsuite_date(invoice.due_date)
    if due_date is None:
        findings.append(
            RiskFinding(
                code="missing_due_date",
                title="Missing due date",
                detail="The duedate field is missing or could not be parsed.",
                score=10,
                fields=["duedate"],
            )
        )
        suggested_checks.append("Confirm payment timing before approval.")
        return

    if due_date < today:
        findings.append(
            RiskFinding(
                code="due_date_passed",
                title="Due date has passed",
                detail=f"Due date {invoice.due_date} is before review date {today.isoformat()}.",
                score=15,
                fields=["duedate"],
            )
        )
        suggested_checks.append("Confirm whether the invoice is still pending or already handled.")
    elif due_date <= today + timedelta(days=3):
        findings.append(
            RiskFinding(
                code="due_within_3_days",
                title="Due within 3 days",
                detail=f"Due date {invoice.due_date} is close to review date {today.isoformat()}.",
                score=15,
                fields=["duedate"],
            )
        )
        suggested_checks.append("Prioritize review if payment is still required.")


def invoice_has_code(findings: list[RiskFinding], code: str) -> bool:
    return any(finding.code == code for finding in findings)


def dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def format_money(amount: float) -> str:
    return f"{amount:,.2f}"
