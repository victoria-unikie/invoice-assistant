# Invoice Review Assistant MVP

Invoice Review Assistant is a small Python MVP for reviewing incoming NetSuite vendor bills before finance approval. It reads a NetSuite-style JSON export, compares the newest bill with previous bills from the same vendor, assigns a simple risk score, and generates Microsoft Teams Adaptive Card JSON for human review.

The project is intentionally lightweight: no database, no web server, no NetSuite write-back, and no real Teams delivery yet. It is designed as a hackathon/internal prototype that demonstrates the invoice review workflow end to end using local files.

## What It Does

- Reads `bill_example.json`, a NetSuite vendor bill export.
- Preserves the original NetSuite field names from the input payload.
- Treats the newest bill in `records` as the invoice under review.
- Uses the earlier records from the same vendor as historical comparison data.
- Normalizes invoice fields into small typed Python models.
- Applies deterministic risk rules for common finance review cases.
- Produces a Teams Adaptive Card JSON file in `cards/invoice_review_card.example.json`.
- Includes reviewer actions such as approve, needs clarification, decline, assign owner, open in NetSuite, and add comment.
- Masks full bank account details in the generated card output.

## Current Sample Result

With the included `bill_example.json`, the MVP reviews invoice `30300003236` from `Kip Infra Oy`.

Using this command:

```bash
python3 -B -m src.main bill_example.json --today 2026-06-24
```

the generated assessment is:

```text
Unknown risk / score 15 for invoice 30300003236 from Kip Infra Oy
```

The risk is `unknown` because the sample export does not include detailed invoice line rows, so line-item comparison cannot be performed. The score is `15` because the invoice due date has already passed relative to the review date used in the demo.

## Generated Adaptive Card

The generated card is valid Adaptive Card JSON and is written to:

```text
cards/invoice_review_card.example.json
```

The card includes:

- Invoice review title and warning marker.
- Vendor, invoice number, amount, due date, and risk badge.
- Reasons why the invoice was flagged.
- Recommended checks for the finance reviewer.
- Invoice highlights such as reference, masked bank account, and payment timing.
- A compact line-item style table.
- Missing-field summary.
- Comment and owner inputs.
- Actions:
  - Approve
  - Needs clarification
  - Decline
  - Assign owner
  - Open in NetSuite
  - Add comment

Note: `bill_example.json` does not include actual detailed line rows. When line rows are unavailable, the card uses the bill memo and header totals as a compact display fallback and clearly states that detailed line rows were not present in the export.

## Risk Rules

The MVP currently checks:

- Missing required reference fields.
- No vendor history.
- Amount more than 20 percent above vendor average.
- Amount more than 50 percent above vendor average.
- New currency for the vendor.
- Changed bank account/payment detail field.
- Possible duplicate invoice number.
- Missing or past/near due date.
- Missing invoice line-item detail.

Risk levels:

- `low`: score 0-20
- `medium`: score 21-50
- `high`: score 51-100
- `unknown`: insufficient history or missing comparison data

Unknown risk is routed to human review.

## Project Structure

```text
.
|-- AGENT.md
|-- README.md
|-- bill_example.json
|-- cards
|   |-- ex1.json
|   `-- invoice_review_card.example.json
|-- src
|   |-- __init__.py
|   |-- main.py
|   |-- risk_engine
|   |   |-- __init__.py
|   |   |-- models.py
|   |   |-- normalizer.py
|   |   `-- scoring.py
|   `-- teams
|       |-- __init__.py
|       `-- card_builder.py
`-- tests
    `-- test_smoke.py
```

## Code Overview

### `src/main.py`

CLI entry point. It reads the input file, runs scoring, builds the Adaptive Card, writes the output JSON, and prints a short summary.

### `src/risk_engine/models.py`

Contains the core typed data structures:

- `Invoice`
- `VendorHistory`
- `RiskFinding`
- `RiskAssessment`

The project uses standard-library `dataclasses` to keep the MVP dependency-free.

### `src/risk_engine/normalizer.py`

Loads the NetSuite JSON export, keeps the original source field names, extracts important invoice fields, parses dates, and separates the newest invoice from vendor history.

### `src/risk_engine/scoring.py`

Contains the deterministic risk scoring logic. It adds findings, assigns point values, calculates the final score, classifies risk level, and decides whether the invoice should be routed to review.

### `src/teams/card_builder.py`

Builds the Teams Adaptive Card JSON. It formats the finance review message, masks bank account values, builds the invoice summary, creates the line-item display, and defines reviewer actions.

### `tests/test_smoke.py`

Small smoke test that verifies the sample invoice can be loaded, scored, and converted into an Adaptive Card without leaking the full bank account value.

## Requirements

- Python 3.11 or newer recommended.
- No third-party dependencies are required for the current MVP.

## Running Locally

From the repository root:

```bash
python3 -B -m src.main bill_example.json --today 2026-06-24
```

Optional custom output path:

```bash
python3 -B -m src.main bill_example.json \
  --today 2026-06-24 \
  --output cards/my_invoice_card.json
```

Optional NetSuite base URL for the `Open in NetSuite` button:

```bash
python3 -B -m src.main bill_example.json \
  --today 2026-06-24 \
  --netsuite-base-url https://example.app.netsuite.com
```

When no NetSuite base URL is provided, `Open in NetSuite` is emitted as an `Action.Submit` placeholder instead of an external URL.

## Running Tests

```bash
python3 -B -m unittest tests.test_smoke
```

Expected output:

```text
Ran 1 test

OK
```

## Data Safety

This MVP is designed to avoid committing sensitive production data.

Current safeguards:

- The generated card masks the full bank account value.
- `.env.local` is ignored for local secrets.
- Python cache files and virtual environments are ignored.
- The included data should be treated as sample/demo data only.

Do not commit:

- API keys or tokens.
- Tenant IDs.
- Real bank account details.
- Personal data.
- Real invoice PDFs.
- Confidential vendor data.

## Current Limitations

- No live NetSuite API integration.
- No Power Automate webhook sender yet.
- No database or persistence layer.
- No real approval write-back.
- No full Teams Bot implementation.
- No Pydantic models yet; the current MVP uses dataclasses to avoid dependencies.
- The included sample export has no detailed line rows, so line-item comparison is limited.
- Adaptive Card styling is limited by what Microsoft Teams supports for Adaptive Cards.

## Suggested Next Steps

- Add a sample payload with real invoice line rows.
- Add `data/sample_vendor_history.json` and `data/sample_upcoming_invoices.json`.
- Add a Power Automate webhook sender.
- Add optional Pydantic validation.
- Add fuzzy line-item matching with `rapidfuzz`.
- Add configurable risk thresholds.
- Add more demo cases:
  - Normal recurring low-risk invoice.
  - Amount spike.
  - New unseen line item.
  - Unknown history and missing buyer reference.
  - Possible duplicate invoice.

## MVP Philosophy

This project favors simple, deterministic rules over complex ML. The goal is to give finance reviewers a concise, explainable reason why an invoice needs review, while keeping the code small enough to understand and adapt quickly.
