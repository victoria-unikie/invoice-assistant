from __future__ import annotations

import os
from typing import Any

from src.risk_engine.models import Invoice, RiskAssessment, RiskFinding
from src.risk_engine.normalizer import parse_netsuite_date
from src.risk_engine.scoring import format_money


CURRENCY_LABELS = {
    "1": "EUR",
}

MONTHS = {
    1: "Jan",
    2: "Feb",
    3: "Mar",
    4: "Apr",
    5: "May",
    6: "Jun",
    7: "Jul",
    8: "Aug",
    9: "Sep",
    10: "Oct",
    11: "Nov",
    12: "Dec",
}


def build_teams_card(assessment: RiskAssessment, netsuite_base_url: str | None = None) -> dict[str, Any]:
    invoice = assessment.invoice
    title = "Invoice needs review" if assessment.route_to_review else "Low-risk invoice candidate"
    findings = assessment.findings or [
        RiskFinding(
            code="no_findings",
            title="No unusual checks triggered",
            detail="No unusual checks triggered against the available vendor history.",
            score=0,
        )
    ]

    body: list[dict[str, Any]] = [
        title_row(title),
        invoice_summary_row(assessment),
        {
            "type": "TextBlock",
            "text": "Why this was flagged",
            "weight": "Bolder",
            "color": "Attention",
            "spacing": "Medium",
            "separator": True,
            "wrap": True,
        },
        {"type": "TextBlock", "text": bullet_text([finding.detail for finding in findings[:4]]), "wrap": True},
        {
            "type": "TextBlock",
            "text": "Recommended checks",
            "weight": "Bolder",
            "color": "Accent",
            "spacing": "Medium",
            "wrap": True,
        },
        {"type": "TextBlock", "text": bullet_text(assessment.suggested_checks[:4]), "wrap": True},
        {
            "type": "TextBlock",
            "text": "Invoice highlights",
            "weight": "Bolder",
            "color": "Accent",
            "spacing": "Medium",
            "wrap": True,
        },
        invoice_highlights_row(invoice),
        {
            "type": "TextBlock",
            "text": "Line items",
            "weight": "Bolder",
            "spacing": "Medium",
            "wrap": True,
        },
        line_items_table(invoice),
        {
            "type": "TextBlock",
            "text": line_item_note(invoice),
            "isSubtle": True,
            "size": "Small",
            "wrap": True,
        },
        {
            "type": "TextBlock",
            "text": "Key missing fields",
            "weight": "Bolder",
            "spacing": "Medium",
            "wrap": True,
        },
        {"type": "TextBlock", "text": bullet_text(missing_field_summary(assessment)), "wrap": True},
        {
            "type": "Input.Text",
            "id": "comment",
            "placeholder": "Add comment",
            "isMultiline": True,
        },
        {
            "type": "Input.Text",
            "id": "owner",
            "placeholder": "Assign owner",
        },
    ]

    netsuite_url = build_netsuite_url(invoice, netsuite_base_url)
    open_action: dict[str, Any]
    if netsuite_url:
        open_action = {"type": "Action.OpenUrl", "title": "Open in NetSuite", "url": netsuite_url}
    else:
        open_action = {
            "type": "Action.Submit",
            "title": "Open in NetSuite",
            "data": action_payload(invoice, "open_in_netsuite"),
        }

    actions: list[dict[str, Any]] = [
        {
            "type": "Action.Submit",
            "title": "Approve",
            "style": "positive",
            "data": action_payload(invoice, "approve"),
        },
        {
            "type": "Action.Submit",
            "title": "Needs clarification",
            "style": "default",
            "data": action_payload(invoice, "needs_clarification"),
        },
        {
            "type": "Action.Submit",
            "title": "Decline",
            "style": "destructive",
            "data": action_payload(invoice, "decline"),
        },
        {"type": "Action.Submit", "title": "Assign owner", "data": action_payload(invoice, "assign_owner")},
        open_action,
        {"type": "Action.Submit", "title": "Add comment", "data": action_payload(invoice, "add_comment")},
    ]

    return {
        "$schema": "https://adaptivecards.io/schemas/adaptive-card.json",
        "type": "AdaptiveCard",
        "version": "1.5",
        "body": body,
        "actions": actions,
    }


def title_row(title: str) -> dict[str, Any]:
    return {
        "type": "ColumnSet",
        "columns": [
            {
                "type": "Column",
                "width": "auto",
                "verticalContentAlignment": "Center",
                "items": [
                    {
                        "type": "TextBlock",
                        "text": "!",
                        "color": "Attention",
                        "size": "ExtraLarge",
                        "weight": "Bolder",
                        "spacing": "None",
                    }
                ],
            },
            {
                "type": "Column",
                "width": "stretch",
                "verticalContentAlignment": "Center",
                "items": [
                    {
                        "type": "TextBlock",
                        "text": title,
                        "weight": "Bolder",
                        "size": "Large",
                        "wrap": True,
                        "spacing": "None",
                    }
                ],
            },
        ],
    }


def invoice_summary_row(assessment: RiskAssessment) -> dict[str, Any]:
    invoice = assessment.invoice
    return {
        "type": "ColumnSet",
        "spacing": "Medium",
        "columns": [
            summary_column("Vendor", invoice.vendor_name),
            summary_column("Invoice number", invoice.tranid),
            summary_column("Amount", display_amount(invoice)),
            summary_column("Due date", display_date(invoice.due_date)),
            risk_column(assessment),
        ],
    }


def summary_column(label: str, value: str) -> dict[str, Any]:
    return {
        "type": "Column",
        "width": "stretch",
        "items": [
            {"type": "TextBlock", "text": label, "isSubtle": True, "size": "Small", "wrap": True},
            {"type": "TextBlock", "text": value, "weight": "Bolder", "wrap": True, "spacing": "None"},
        ],
    }


def risk_column(assessment: RiskAssessment) -> dict[str, Any]:
    return {
        "type": "Column",
        "width": "auto",
        "items": [
            {"type": "TextBlock", "text": "Risk", "isSubtle": True, "size": "Small", "wrap": True},
            {
                "type": "Container",
                "style": risk_style(assessment.risk_level),
                "bleed": False,
                "items": [
                    {
                        "type": "TextBlock",
                        "text": f"{assessment.risk_level.title()} {assessment.risk_score}",
                        "weight": "Bolder",
                        "horizontalAlignment": "Center",
                        "spacing": "None",
                        "wrap": True,
                    }
                ],
            },
        ],
    }


def risk_style(risk_level: str) -> str:
    if risk_level == "low":
        return "good"
    if risk_level == "medium":
        return "warning"
    return "attention"


def invoice_highlights_row(invoice: Invoice) -> dict[str, Any]:
    return {
        "type": "ColumnSet",
        "columns": [
            highlight_column("Reference", invoice.reference_text or invoice.reference_number or "n/a"),
            highlight_column("Bank", mask_bank_account(invoice.bank_account)),
            highlight_column("Payment terms", f"due {display_date(invoice.due_date)}"),
        ],
    }


def highlight_column(label: str, value: str) -> dict[str, Any]:
    return {
        "type": "Column",
        "width": "stretch",
        "items": [
            {"type": "TextBlock", "text": label, "isSubtle": True, "size": "Small", "wrap": True},
            {"type": "TextBlock", "text": value, "weight": "Bolder", "spacing": "None", "wrap": True},
        ],
    }


def line_items_table(invoice: Invoice) -> dict[str, Any]:
    return {
        "type": "Container",
        "style": "emphasis",
        "items": [
            line_table_row(
                ["Line", "Description", "Qty", "Unit price", "Net", "VAT %", "Gross"],
                header=True,
            ),
            *line_table_rows(invoice),
        ],
    }


def line_table_rows(invoice: Invoice) -> list[dict[str, Any]]:
    if invoice.line_items:
        rows = []
        for index, item in enumerate(invoice.line_items[:4], start=1):
            rows.append(
                line_table_row(
                    [
                        str(index),
                        str(item.get("description") or item.get("memo") or "Line item"),
                        str(item.get("quantity") or "1"),
                        money_or_na(item.get("unit_price")),
                        money_or_na(item.get("net_amount")),
                        percent_or_na(item.get("vat_percent") or item.get("tax_percent")),
                        money_or_na(item.get("gross_amount") or item.get("amount")),
                    ]
                )
            )
        return rows

    return [
        line_table_row(
            [
                "1",
                invoice.memo or "Header total from export",
                "1",
                money_or_na(invoice.raw.get("custbody_stc_amount_after_discount")),
                money_or_na(invoice.raw.get("custbody_stc_amount_after_discount")),
                estimated_vat_percent(invoice),
                money_or_na(invoice.raw.get("custbody_stc_total_after_discount") or invoice.amount),
            ]
        )
    ]


def line_table_row(values: list[str], header: bool = False) -> dict[str, Any]:
    return {
        "type": "ColumnSet",
        "separator": not header,
        "spacing": "Small",
        "columns": [
            table_cell(values[0], "auto", header),
            table_cell(values[1], "stretch", header),
            table_cell(values[2], "auto", header),
            table_cell(values[3], "auto", header),
            table_cell(values[4], "auto", header),
            table_cell(values[5], "auto", header),
            table_cell(values[6], "auto", header),
        ],
    }


def table_cell(value: str, width: str, header: bool = False) -> dict[str, Any]:
    return {
        "type": "Column",
        "width": width,
        "items": [
            {
                "type": "TextBlock",
                "text": value,
                "size": "Small",
                "weight": "Bolder" if header else "Default",
                "wrap": True,
                "spacing": "None",
            }
        ],
    }


def risk_summary(assessment: RiskAssessment) -> str:
    if assessment.risk_level == "unknown":
        return "Risk is unknown because evidence is limited; this invoice needs review."
    if assessment.risk_level == "low":
        return "Low risk based on the available vendor history."
    return f"{assessment.risk_level.title()} risk invoice needs review."


def bullet_text(values: list[str]) -> str:
    if not values:
        return "- None"
    return "\n".join(f"- {value}" for value in values)


def missing_field_summary(assessment: RiskAssessment) -> list[str]:
    values = list(assessment.missing_fields)
    if not assessment.invoice.line_items:
        values.append("invoice_lines / line_items not present in export")
    if "cost center" not in values:
        values.append("cost center field not present in export")
    if "approver" not in values:
        values.append("approver/reviewer field not present in export")
    return values or ["No key fields missing from the available export"]


def line_item_summary(invoice: Invoice) -> str:
    if invoice.line_items:
        rows = []
        for item in invoice.line_items[:3]:
            description = item.get("description") or item.get("memo") or "line item"
            amount = item.get("gross_amount") or item.get("amount") or item.get("net_amount") or "n/a"
            rows.append(f"- {description}: {amount}")
        return "\n".join(rows)

    net = invoice.raw.get("custbody_stc_amount_after_discount")
    tax = invoice.raw.get("custbody_stc_tax_after_discount")
    parts = ["Line item details are not present in bill_example.json."]
    if invoice.memo:
        parts.append(f"Memo: {invoice.memo}.")
    if net is not None or tax is not None:
        parts.append(f"Available totals: net {net or 'n/a'}, tax {tax or 'n/a'}.")
    return " ".join(parts)


def line_item_note(invoice: Invoice) -> str:
    if invoice.line_items:
        return "Only the first four line items are shown."
    return "Detailed line rows were not present in the export, so this table uses memo and header totals only."


def display_amount(invoice: Invoice) -> str:
    return f"{format_money(invoice.amount)} {currency_label(invoice.currency)}"


def currency_label(currency: str) -> str:
    return CURRENCY_LABELS.get(currency, currency)


def display_date(value: str | None) -> str:
    parsed = parse_netsuite_date(value)
    if not parsed:
        return value or "n/a"
    return f"{parsed.day} {MONTHS[parsed.month]} {parsed.year}"


def mask_bank_account(value: str | None) -> str:
    if not value:
        return "n/a"
    if len(value) <= 8:
        return value
    return f"{value[:4]} ... {value[-4:]}"


def money_or_na(value: Any) -> str:
    try:
        return format_money(float(value))
    except (TypeError, ValueError):
        return "n/a"


def percent_or_na(value: Any) -> str:
    try:
        return f"{float(value):.2f}%"
    except (TypeError, ValueError):
        return "n/a"


def estimated_vat_percent(invoice: Invoice) -> str:
    net = invoice.raw.get("custbody_stc_amount_after_discount")
    tax = invoice.raw.get("custbody_stc_tax_after_discount")
    try:
        net_amount = float(net)
        tax_amount = float(tax)
    except (TypeError, ValueError):
        return "n/a"
    if net_amount == 0:
        return "n/a"
    return f"{(tax_amount / net_amount) * 100:.2f}%"


def action_payload(invoice: Invoice, action: str) -> dict[str, Any]:
    return {
        "action": action,
        "record_type": invoice.raw.get("recordtype"),
        "record_id": invoice.id,
        "tranid": invoice.tranid,
        "vendor_id": invoice.vendor_id,
    }


def build_netsuite_url(invoice: Invoice, netsuite_base_url: str | None) -> str | None:
    base_url = netsuite_base_url or os.getenv("NETSUITE_BASE_URL")
    if not base_url or not invoice.id:
        return None
    return f"{base_url.rstrip('/')}/app/accounting/transactions/vendbill.nl?id={invoice.id}"
