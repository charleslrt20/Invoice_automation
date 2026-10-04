# Workflow: Send Invoice

## Objective

Generate a professional PDF invoice and deliver it to a customer via email, archive it in Google Drive, and log the record to Google Sheets — all triggered from a single form submission on the web dashboard.

## Entry Point

Web dashboard at `http://localhost:8848` (protected by HTTP Basic Auth — `APP_USERNAME` / `APP_PASSWORD`)
API endpoint: `POST /api/invoices/send`

## Required Inputs

| Field            | Type   | Notes                                              |
| ---------------- | ------ | --------------------------------------------------|
| invoice_number   | string | Unique identifier (e.g. INV-001)                   |
| invoice_date     | date   | YYYY-MM-DD                                         |
| due_date         | date   | YYYY-MM-DD                                         |
| customer_name    | string |                                                     |
| customer_email   | email  |                                                     |
| customer_address | string | Full billing address                               |
| line_items       | array  | At least one: {description, quantity, unit_price}  |
| vat_rate         | float  | Percentage, e.g. 23                                |
| notes            | string | Optional payment terms                             |
| language         | string | `"en"` or `"fr"` — defaults to `"en"`               |

Company branding (name, address, VAT, phone, email, logo) loaded automatically from `.env`.

## Pipeline

```
POST /api/invoices/send (server.py)
│
├── 1. Compute financials (server-side, not trusted from client)
│      subtotal  = sum(qty × unit_price)
│      vat_amount = subtotal × vat_rate / 100
│      total     = subtotal + vat_amount
│
├── 2. tools/generate_pdf.py → generate_invoice_pdf()
│      Render the invoice directly with fpdf2 (no HTML/Jinja2 step)
│      Text rendered with Liberation Sans (fonts/LiberationSans-{Regular,Bold}.ttf)
│      Supports English and French output via the `language` field
│      ↳ CRITICAL: abort pipeline with HTTP 500 on failure
│
├── 3. tools/send_email.py → send_invoice_email()
│      Attach PDF via Gmail SMTP (smtp.gmail.com:587, STARTTLS)
│      Subject: "Invoice {number} from {company name}" (or French equivalent)
│      Customer-supplied name/invoice number are stripped of CR/LF before
│      going into email headers to prevent header injection
│      ↳ CRITICAL: abort pipeline with HTTP 502 on failure
│
├── 4. tools/upload_to_drive.py → upload_pdf_to_drive()
│      Upload PDF to GOOGLE_DRIVE_FOLDER_ID
│      Filename: Invoice_{number}_{customer_name}.pdf (sanitized to [\w-] + "_")
│      ↳ NON-CRITICAL: log error in response, continue
│
└── 5. tools/log_to_sheets.py → log_invoice_to_sheets()
       Append row to GOOGLE_SHEETS_ID / GOOGLE_SHEETS_TAB_NAME
       (valueInputOption=RAW — avoids formula/CSV injection from invoice data)
       Columns: Invoice#, Date, Customer, Email, Address,
                Subtotal, VAT%, VAT Amount, Total, Notes,
                Drive URL, Status="Sent"
       ↳ NON-CRITICAL: log error in response, continue
```

## Outputs

- Customer receives email with PDF invoice attached
- PDF stored in Google Drive folder
- Invoice row appended to Google Sheets log

## Success Response Shape

```json
{
  "invoice_number": "INV-001",
  "steps": {
    "pdf": { "success": true },
    "email": { "success": true, "status_code": 250, "message": "Email sent" },
    "drive": {
      "success": true,
      "file_id": "1ABC...",
      "file_url": "https://drive.google.com/..."
    },
    "sheets": { "success": true, "updated_range": "Invoices!A2:L2" }
  }
}
```

## Error Handling

| Step           | Failure Behaviour                                                 |
| -------------- | ------------------------------------------------------------------|
| PDF generation | HTTP 500 — pipeline aborts, error shown in dashboard               |
| Email send     | HTTP 502 — pipeline aborts (no point logging unsent invoice)       |
| Drive upload   | Non-critical — error logged in `steps.drive`, pipeline continues   |
| Sheets log     | Non-critical — error logged in `steps.sheets`, pipeline continues  |

## Prerequisites Checklist

- [ ] `pip3 install -r requirements.txt`
- [ ] `.env` populated with all keys (copy `.env.example` → `.env`, see below)
- [ ] `credentials.json` in project root (from Google Cloud Console → OAuth 2.0 Desktop Client)
- [ ] Google Sheets spreadsheet created; header row on row 1; tab named "Invoices" (or matching `GOOGLE_SHEETS_TAB_NAME`)
- [ ] Google Drive folder created; ID copied to `GOOGLE_DRIVE_FOLDER_ID`
- [ ] Gmail App Password generated for `GMAIL_APP_PASSWORD` (not your regular Gmail password)
- [ ] First run: complete browser OAuth consent → `token.json` auto-generated

## Environment Variables (.env)

See `.env.example` for the full template. Summary:

```dotenv
APP_USERNAME="..."
APP_PASSWORD="..."

COMPANY_NAME="Your Plumbing Co."
COMPANY_ADDRESS="123 Pipe Street, Dublin, D01 AB12"
COMPANY_EMAIL="invoices@yourplumbingco.ie"
COMPANY_PHONE="+353 1 234 5678"
COMPANY_VAT="IE1234567T"
COMPANY_LOGO_PATH=""

GMAIL_ADDRESS="you@gmail.com"
GMAIL_APP_PASSWORD="xxxx xxxx xxxx xxxx"
GMAIL_FROM_NAME="Your Plumbing Co."

GOOGLE_DRIVE_FOLDER_ID="1ABC..."
GOOGLE_SHEETS_ID="1DEF..."
GOOGLE_SHEETS_TAB_NAME="Invoices"
```

## Running the Server

```bash
uvicorn server:app --reload --port 8848
```

Open `http://localhost:8848` and log in with `APP_USERNAME` / `APP_PASSWORD`.

## Known Constraints

- PDFs are generated directly with `fpdf2` — `templates/invoice.html` is unused legacy and not part of the active pipeline
- `COMPANY_LOGO_PATH` must be a local file path relative to the project root, not an HTTP URL
- Gmail sending limits apply (~500/day on a standard Gmail account; higher on Google Workspace) — switch providers if volume grows
- Google OAuth token auto-refreshes but the very first run requires interactive browser consent (cannot be headless)
- `token.json` stores a long-lived refresh token — treat it like a credential and keep it out of version control (already in `.gitignore`)
- `credentials.json` and `.env` are also gitignored — never commit real values; use `.env.example` as the template for new setups
