from datetime import date
from pathlib import Path
import unittest

from src.risk_engine.normalizer import load_invoice_and_history
from src.risk_engine.scoring import assess_invoice
from src.teams.card_builder import build_teams_card


class InvoiceCardSmokeTest(unittest.TestCase):
    def test_bill_example_builds_review_card(self) -> None:
        invoice, history = load_invoice_and_history(Path("bill_example.json"))
        assessment = assess_invoice(invoice, history, date(2026, 6, 24))
        card = build_teams_card(assessment)

        self.assertEqual(card["type"], "AdaptiveCard")
        self.assertEqual(assessment.invoice.tranid, "30300003236")
        self.assertEqual(assessment.risk_level, "unknown")
        self.assertTrue(any(action["title"] == "Approve" for action in card["actions"]))
        self.assertTrue(any(action["title"] == "Decline" and action["style"] == "destructive" for action in card["actions"]))
        self.assertNotIn("FI7351620020141076", str(card))


if __name__ == "__main__":
    unittest.main()
