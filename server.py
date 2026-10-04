import os
import re
import secrets
import sys
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv

load_dotenv()

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, EmailStr, field_validator

# Ensure tools/ is importable
sys.path.insert(0, str(Path(__file__).parent))

from tools.generate_pdf import generate_invoice_pdf
from tools.send_email import send_invoice_email
from tools.upload_to_drive import upload_pdf_to_drive
from tools.log_to_sheets import log_invoice_to_sheets

security = HTTPBasic(realm="Invoice Automation")


def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(
        credentials.username.encode(), os.getenv("APP_USERNAME", "").encode()
    )
    correct_password = secrets.compare_digest(
        credentials.password.encode(), os.getenv("APP_PASSWORD", "").encode()
    )
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )


app = FastAPI(title="Invoice Automation", dependencies=[Depends(verify_credentials)])

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8848", "http://127.0.0.1:8848"],
    allow_methods=["POST", "GET"],
    allow_headers=["Authorization", "Content-Type"],
)


class LineItem(BaseModel):
    description: str
    quantity: float
    unit_price: float


class InvoiceRequest(BaseModel):
    invoice_number: str
    invoice_date: str
    due_date: str
    customer_name: str
    customer_email: EmailStr
    customer_address: str
    line_items: List[LineItem]
    vat_rate: float
    notes: Optional[str] = ""
    language: str = "en"

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: str) -> str:
        if v not in ("en", "fr"):
            raise ValueError("language must be 'en' or 'fr'")
        return v


@app.get("/")
async def serve_frontend():
    return FileResponse(Path(__file__).parent / "index.html")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/invoices/send")
async def send_invoice(invoice: InvoiceRequest):
    company = {
        "name":      os.environ["COMPANY_NAME"],
        "address":   os.environ["COMPANY_ADDRESS"],
        "email":     os.environ["COMPANY_EMAIL"],
        "phone":     os.environ["COMPANY_PHONE"],
        "vat":       os.environ["COMPANY_VAT"],
        "logo_path": os.environ.get("COMPANY_LOGO_PATH", ""),
    }

    line_items = [item.model_dump() for item in invoice.line_items]
    subtotal   = sum(i["quantity"] * i["unit_price"] for i in line_items)
    vat_amount = subtotal * invoice.vat_rate / 100
    total      = subtotal + vat_amount

    invoice_dict = invoice.model_dump()
    invoice_dict["line_items"] = line_items
    invoice_dict.update({"subtotal": subtotal, "vat_amount": vat_amount, "total": total})

    pipeline = {"invoice_number": invoice.invoice_number, "steps": {}}

    # Step 1 – Generate PDF
    try:
        pdf_bytes = generate_invoice_pdf(invoice_dict, company, language=invoice.language)
        pipeline["steps"]["pdf"] = {"success": True}
    except Exception:
        raise HTTPException(status_code=500, detail="PDF generation failed")

    # Step 2 – Send email (critical — abort if it fails)
    email_result = send_invoice_email(
        to_email=invoice.customer_email,
        to_name=invoice.customer_name,
        invoice_number=invoice.invoice_number,
        pdf_bytes=pdf_bytes,
        company=company,
        language=invoice.language,
    )
    pipeline["steps"]["email"] = email_result
    if not email_result["success"]:
        raise HTTPException(status_code=502, detail="Email delivery failed")

    # Step 3 – Upload to Google Drive (non-critical)
    safe_name = re.sub(r"[^\w\-]", "_", invoice.customer_name)
    safe_num  = re.sub(r"[^\w\-]", "_", invoice.invoice_number)
    filename  = f"Invoice_{safe_num}_{safe_name}.pdf"
    drive_result = upload_pdf_to_drive(
        pdf_bytes=pdf_bytes,
        filename=filename,
        folder_id=os.environ["GOOGLE_DRIVE_FOLDER_ID"],
    )
    pipeline["steps"]["drive"] = drive_result

    # Step 4 – Log to Google Sheets (non-critical)
    sheets_result = log_invoice_to_sheets(
        invoice_data=invoice_dict,
        subtotal=subtotal,
        vat_amount=vat_amount,
        total=total,
        drive_url=drive_result.get("file_url") or "",
        spreadsheet_id=os.environ["GOOGLE_SHEETS_ID"],
        tab_name=os.environ.get("GOOGLE_SHEETS_TAB_NAME", "Invoices"),
    )
    pipeline["steps"]["sheets"] = sheets_result

    return JSONResponse(content=pipeline)
