from __future__ import annotations

import argparse
import json
from datetime import date, datetime
from pathlib import Path

from src.risk_engine.normalizer import load_invoice_and_history
from src.risk_engine.scoring import assess_invoice
from src.teams.card_builder import build_teams_card


def parse_today(value: str | None) -> date:
    if value:
        return datetime.strptime(value, "%Y-%m-%d").date()
    return date.today()


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a Teams Adaptive Card from a NetSuite bill export.")
    parser.add_argument("input", nargs="?", default="bill_example.json", help="Path to bill_example.json")
    parser.add_argument(
        "--output",
        default="cards/invoice_review_card.example.json",
        help="Where to write the Adaptive Card JSON",
    )
    parser.add_argument("--today", help="Review date as YYYY-MM-DD. Defaults to today's date.")
    parser.add_argument("--netsuite-base-url", help="Optional NetSuite account base URL for the Open action.")
    args = parser.parse_args()

    invoice, history = load_invoice_and_history(Path(args.input))
    assessment = assess_invoice(invoice, history, parse_today(args.today))
    card = build_teams_card(assessment, args.netsuite_base_url)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(card, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"Wrote {output_path}")
    print(
        f"{assessment.risk_level.title()} risk / score {assessment.risk_score} "
        f"for invoice {invoice.tranid} from {invoice.vendor_name}"
    )


if __name__ == "__main__":
    main()
