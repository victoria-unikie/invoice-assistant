# AGENTS.md

## Project

Invoice Review Assistant MVP.

This project helps the finance department identify unusual, risky, duplicate, incomplete, or low-risk incoming vendor bills from NetSuite. The assistant evaluates upcoming invoices, assigns a risk score, and sends actionable Microsoft Teams Adaptive Cards for invoices that need human review.

The MVP should be treated as an internal finance workflow prototype, but code should be structured cleanly enough to evolve into a production system.

## Core Flow

NetSuite incoming vendor bills
→ Invoice normalization
→ Historical invoice comparison
→ Risk scoring / rules engine
→ Low-risk auto-approval candidate or human review
→ Teams Adaptive Card through Power Automate
→ Reviewer decision/comment
→ Optional NetSuite write-back later

## Tech Stack

Use Python for the backend and risk engine.

Preferred stack:
- Python 3.11+
- FastAPI for API endpoints
- Pydantic for typed invoice/risk models
- httpx or requests for external HTTP calls
- python-dotenv / pydantic-settings for configuration
- rapidfuzz for fuzzy matching invoice line descriptions
- Adaptive Card JSON for Microsoft Teams cards
- Power Automate for posting Teams cards and waiting for user responses

Do not implement a full Teams Bot unless explicitly requested. Default Teams integration is Adaptive Cards through Power Automate.

## Repository Structure

Expected structure:

/src
  /risk_engine
  /teams
  /netsuite
/data
/cards
/tests
README.md
AGENTS.md

Recommended files:

/src/main.py
/src/config.py
/src/risk_engine/models.py
/src/risk_engine/normalizer.py
/src/risk_engine/rules.py
/src/risk_engine/scoring.py
/src/risk_engine/guidance.py
/src/netsuite/client.py
/src/netsuite/queries.py
/src/netsuite/mapper.py
/src/teams/card_builder.py
/src/teams/power_automate.py
/cards/invoice_review_card.template.json
/cards/invoice_review_card.example.json
/data/sample_upcoming_invoices.json
/data/sample_vendor_history.json

## MVP Scope

The MVP must:
- Fetch or accept upcoming invoices from NetSuite as JSON.
- Use the sample payload in bill_example.json as the reference schema for field names.
- Preserve the field names from that JSON when normalizing and processing invoice data.
- Normalize invoice fields into internal Pydantic models.
- Compare current invoices with historical invoices from the same vendor.
- Detect amount anomalies.
- Detect new or changed line items.
- Detect missing required references.
- Detect possible duplicate invoices.
- Detect missing or changed payment/vendor details when data is available.
- Assign a risk score from 0 to 100.
- Classify risk as low, medium, high, or unknown.
- Generate Teams Adaptive Card JSON.
- Send medium, high, and unknown risk invoices to finance review.
- Mark low-risk invoices as auto-approval candidates.
- Capture reviewer action/comment.

## Risk Levels

Use these risk levels:

- Low: 0–20
- Medium: 20–50
- High: 50–100
- Unknown: insufficient history or missing required comparison data

Unknown risk should normally be routed to human review.

## Low-Risk / Auto-Approval Rule

Low-risk invoices may be marked as auto-approval candidates only when:
- Vendor history exists.
- The vendor is known.
- The invoice amount is within the normal historical range.
- Line items are known for this vendor.
- Required approval context is present.
- No duplicate risk is detected.
- No payment detail changes are detected.
- Currency and tax behavior are consistent with history.

For MVP, do not perform real NetSuite approval write-back by default. Use a dry-run recommendation unless explicit write-back is requested.

Use feature flags:

ENABLE_NETSUITE_WRITEBACK=false
ENABLE_AUTO_APPROVAL=false

## Human Review Rule

Send invoices to finance review when:
- Risk is medium, high, or unknown.
- Amount is significantly higher than vendor average.
- Vendor has no or limited history.
- New line items are detected.
- Quantity, unit price, tax, or currency differs from history.
- Required fields are missing.
- Possible duplicate invoice is detected.
- Vendor payment details changed.
- Due date is close.
- The invoice matches a previous risk pattern.

## Suggested Scoring

Default rule scoring may be adjusted, but start with:

- No vendor history: +35
- Amount 20–50% above vendor average: +25
- Amount more than 50% above vendor average: +45
- New line item: +20
- Significant unit price change: +20
- Missing buyer reference: +15
- Missing cost center: +20
- Missing approver: +25
- Possible duplicate invoice: +50
- Changed bank account: +60
- New currency for vendor: +30
- Due within 3 days: +15

Cap final score at 100.

## Language and Tone

Teams messages should be in concise business English unless otherwise requested.

Use:
- “needs review”
- “unusual”
- “requires confirmation”
- “matches previous risk pattern”
- “recommended checks”

Avoid:
- “fraud”
- “criminal”
- “definitely wrong”
- vague warnings
- alarmist language

If evidence is limited, say so clearly.

Example:
“Risk is unknown because no previous vendor history is available.”

## Teams Adaptive Card Requirements

Use Adaptive Card JSON.

Each card should include:
- Title
- Vendor
- Invoice number
- Amount and currency
- Due date
- Risk level and score
- Why this was flagged
- Suggested checks
- Key missing fields
- Main line items summary
- Actions

Default actions:
- Approve
- Needs clarification
- Assign owner
- Open in NetSuite
- Add comment

Keep cards short. Do not include full invoice PDF contents or large line item tables. Use NetSuite links for details.

## Power Automate

Default delivery mechanism:
- Power Automate flow
- Microsoft Teams connector
- Post adaptive card to Teams channel and wait for a response

The backend may send Adaptive Card JSON to a Power Automate webhook if available.

If HTTP/webhook access is unavailable, generate card JSON locally and use manual/scheduled Power Automate flow for demo.

## NetSuite Rules

NetSuite is the source of invoice data.

The MVP should fetch upcoming vendor bills and historical vendor invoices.

Needed fields:
- vendor name
- vendor business ID
- invoice number
- invoice date
- due date
- total amount
- currency
- payment terms
- bank account or payment details if available
- buyer reference
- PO number if available
- contract reference
- cost center
- reviewer
- approver
- approval status
- invoice lines

Line item fields:
- description
- product/service ID
- quantity
- unit price
- net amount
- VAT/tax percent
- VAT/tax amount
- gross amount

Do not update NetSuite approvals, payment details, vendor details, or invoice status unless explicitly requested.

## Data Safety

Do not commit:
- secrets
- API keys
- tokens
- tenant IDs
- real bank account details
- personal data
- real invoice PDFs
- confidential vendor data

Use `.env.local` for local secrets.
Use `.env.example` for placeholder configuration.
Use mock or anonymized data in repository examples.

## Testing

No formal tests are required for the hackathon MVP.

However, when practical, add simple smoke checks for:
- invoice normalization
- risk scoring
- Teams card JSON generation

Do not block MVP progress on test coverage.

## Demo Cases

Include these demo cases:
1. Normal recurring invoice with low risk.
2. Hetzner invoice with amount spike.
3. Hetzner invoice with new unseen line item.
4. KIP Infra rent invoice with unknown history and missing buyer reference.
5. Possible duplicate invoice if time allows.

## Coding Style

Keep code simple and readable.
Prefer deterministic rules over complex ML.
Prefer small functions with explicit names.
Use type hints.
Use Pydantic models for structured data.
Avoid overengineering.
Do not add large frameworks unless explicitly requested.

Recommended entity names:
- Invoice
- InvoiceLine
- VendorHistory
- RiskFinding
- RiskAssessment
- TeamsCardPayload
- ReviewDecision

## Default Commands

If using pip:

python -m venv .venv
pip install -r requirements.txt
python -m src.main

If FastAPI server is implemented:

uvicorn src.main:app --reload

No mandatory test command for MVP.