# Invoice Review Assistant MVP

Main launch file:
[src/main.py (line 1)](/unikie-invoice-assistant/src/main.py:1)
This is the project entry point. When you run:
python3 -m src.main bill_example.json --today 2026-06-24
it runs the full flow:
1. reads bill_example.json;
2. calls invoice normalization;
3. calls scoring/risk assessment;
4. calls the Teams card generator;
5. writes the final JSON to cards/invoice_review_card.example.json.

The file that displays/forms the Teams card data:
[src/teams/card_builder.py (line 1)](unikie-invoice-assistant/src/teams/card_builder.py:1)

This is the main file for the card design. It decides what goes inside the Adaptive Card:
- title Invoice needs review;
- vendor;
- invoice number;
- amount;
- due date;
- risk badge;
- Why this was flagged block;
- Recommended checks block;
- Invoice highlights;
- Line items table;
- comment/owner fields;
- buttons: Approve, Needs clarification, Decline, Assign owner, Open in NetSuite, Add comment.

If you want to change the Teams card appearance, texts, block order, buttons, colors, or JSON structure, this is almost always the file: src/teams/card_builder.py.

The final generated card file:
[cards/invoice_review_card.example.json (line 1)](unikie-invoice-assistant/cards/invoice_review_card.example.json:1)
This is the generated output. You can view it, copy it into Adaptive Card Designer, or send it to Power Automate/Teams. But it is better not to edit it manually for long, because the next run of main.py will overwrite it.
The source data file:
[bill_example.json (line 1)](/unikie-invoice-assistant/bill_example.json:1)
This is the sample NetSuite export. It contains the vendor and a list of records. The code takes the newest record as the invoice to review, and uses the previous records as the vendor history.
The normalization file:
[src/risk_engine/normalizer.py (line 1)](unikie-invoice-assistant/src/risk_engine/normalizer.py:1)
It reads bill_example.json and turns raw JSON into convenient Python objects. It is responsible for:
- loading JSON;
- selecting the current invoice;
- separating vendor history;
- reading fields such as tranid, total, duedate, currency, memo;
- parsing dates;
- finding line items, if they exist.
The models file:
[src/risk_engine/models.py (line 1)](unikie-invoice-assistant/src/risk_engine/models.py:1)
This file describes the data structures:
- Invoice — one invoice;
- VendorHistory — previous invoices for the vendor;
- RiskFinding — one risk reason;
- RiskAssessment — the final risk assessment.
This is not business logic, but the “shape of the data” used by the project.
The scoring file:
[src/risk_engine/scoring.py (line 1)](unikie-invoice-assistant/src/risk_engine/scoring.py:1)
This file is responsible for the risk engine. This is where the code decides:
- low / medium / high / unknown;
- what score to assign;
- why the invoice was flagged;
- which checks to suggest to the reviewer.
It checks:
- missing fields;
- no vendor history;
- amount spike;
- new currency;
- changed bank account;
- duplicate invoice number;
- due date;
- missing line items.
The test:
[tests/test_smoke.py (line 1)](/unikie-invoice-assistant/tests/test_smoke.py:1)
A small test that verifies the project works at all:
- invoice loads;
- risk is calculated;
- Adaptive Card is created;
- Decline button exists;
- the full bank account does not appear in the card.
README:
[README.md (line 1)](/unikie-invoice-assistant/README.md:1)