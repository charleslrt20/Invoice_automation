# Invoice Automation

A small self-hosted web app for generating branded PDF invoices and sending them to clients in one click. Submitting the form on the dashboard runs a full pipeline: generate a PDF, email it to the customer, archive a copy in Google Drive, and log the invoice in a Google Sheet.

Supports English and French invoices.

## How it works

```
Browser (index.html)
   │  POST /api/invoices/send
   ▼
FastAPI server (server.py)  — HTTP Basic Auth protected
   │
   ├── 1. Compute totals server-side (never trust client-sent amounts)
   ├── 2. tools/generate_pdf.py   → render the invoice PDF (fpdf2)
   ├── 3. tools/send_email.py    → email the PDF via Gmail SMTP      (required — aborts pipeline on failure)
   ├── 4. tools/upload_to_drive.py → archive the PDF in Google Drive  (best-effort)
   └── 5. tools/log_to_sheets.py   → append a row to Google Sheets    (best-effort)
```

This project follows a **Workflows / Agents / Tools** structure (see [CLAUDE.md](CLAUDE.md)):
- `workflows/` — plain-language SOPs describing what each automation does
- `tools/` — the actual Python scripts that do the work
- `server.py` — the FastAPI app that wires the dashboard to the tools

## Setup

### 1. System dependency

Python packages only — no system libraries (PDF generation uses `fpdf2`, a pure-Python library).

### 2. Install Python dependencies

```bash
pip3 install -r requirements.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Fill in `.env` with your own values — see the table below.

| Variable | Purpose |
| --- | --- |
| `APP_USERNAME` / `APP_PASSWORD` | Login for the dashboard (HTTP Basic Auth) |
| `COMPANY_NAME`, `COMPANY_ADDRESS`, `COMPANY_EMAIL`, `COMPANY_PHONE`, `COMPANY_VAT` | Your business details, printed on every invoice |
| `COMPANY_LOGO_PATH` | Local file path to your logo (optional) — `static/logo.svg` is a generic placeholder; swap in your own logo file locally and point this at it (don't commit a real logo to a public repo) |
| `GMAIL_ADDRESS` / `GMAIL_APP_PASSWORD` | Gmail account used to send invoices — use a [Gmail App Password](https://support.google.com/accounts/answer/185833), never your real password |
| `GMAIL_FROM_NAME` | Display name on outgoing emails |
| `GOOGLE_DRIVE_FOLDER_ID` | Google Drive folder where PDFs are archived |
| `GOOGLE_SHEETS_ID` / `GOOGLE_SHEETS_TAB_NAME` | Spreadsheet + tab where invoices are logged |

### 4. Google OAuth credentials

1. In [Google Cloud Console](https://console.cloud.google.com/), create an OAuth 2.0 **Desktop App** client and download it as `credentials.json` in the project root.
2. On first run, the app will open a browser window for you to grant access to Drive and Sheets. This generates `token.json`, which is reused (and auto-refreshed) afterwards.

`credentials.json` and `token.json` contain secrets and are already excluded via `.gitignore` — never commit them.

### 5. Run the server

```bash
uvicorn server:app --reload --port 8848
```

Open `http://localhost:8848` and log in with your `APP_USERNAME` / `APP_PASSWORD`.

## Security notes

- The dashboard and API are protected by HTTP Basic Auth (`server.py`); credentials are compared using constant-time comparison to avoid timing attacks.
- CORS is locked down to `localhost:8848` by default — update `server.py` if you deploy elsewhere.
- Invoice totals are always recalculated server-side from `line_items`; client-submitted totals are never trusted.
- Google Sheets writes use `RAW` input mode to prevent formula/CSV injection from invoice data.
- Secrets (`.env`, `credentials.json`, `token.json`) are gitignored and must never be committed. Use `.env.example` as a template.
- This app is designed to run locally or behind a trusted network (e.g. a home server or VPN). It is **not** hardened for direct exposure to the public internet — if you do deploy it publicly, put it behind HTTPS (Basic Auth sends credentials in cleartext encoded, not encrypted) and consider rate-limiting the login endpoint.

## Fonts

PDFs are rendered using [Liberation Sans](https://github.com/liberationfonts/liberation-fonts) (`fonts/LiberationSans-Regular.ttf`, `fonts/LiberationSans-Bold.ttf`), a metrically-compatible, SIL Open Font License substitute for Arial. It was swapped in to replace the original Monotype Arial files, which were commercially licensed and not safe to redistribute in a public repository. The license text is included at `fonts/LICENSE-LiberationSans.txt`.

## Known limitations

- `templates/invoice.html` is currently unused by the PDF pipeline (PDFs are generated directly with `fpdf2`, not HTML/Jinja2 rendering) — leftover from an earlier design.
