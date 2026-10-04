import os
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.header import Header
from email.utils import formataddr
from html import escape

_CRLF = re.compile(r"[\r\n]")


def _strip_crlf(value: str) -> str:
    return _CRLF.sub(" ", value)


def send_invoice_email(
    to_email: str,
    to_name: str,
    invoice_number: str,
    pdf_bytes: bytes,
    company: dict,
    language: str = "en",
) -> dict:
    gmail_address = os.environ["GMAIL_ADDRESS"]
    gmail_app_password = os.environ["GMAIL_APP_PASSWORD"]
    from_name = os.environ.get("GMAIL_FROM_NAME", company["name"])

    to_name = _strip_crlf(to_name)
    invoice_number = _strip_crlf(invoice_number)

    e_inv  = escape(invoice_number)
    e_name = escape(to_name)
    e_co   = escape(company["name"])
    e_addr = escape(company["address"])
    e_ph   = escape(company["phone"])
    e_mail = escape(company["email"])

    if language == "fr":
        subject = f"Facture {invoice_number} de {company['name']}"
        html_body = f"""
        <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;color:#333;">
          <h2 style="color:#1a3a6b;">Facture {e_inv}</h2>
          <p>Bonjour {e_name},</p>
          <p>Veuillez trouver votre facture en pièce jointe.</p>
          <p>Pour toute question, n'hésitez pas à répondre à cet email ou à nous contacter à
             <a href="mailto:{e_mail}">{e_mail}</a>.</p>
          <p>Merci de votre confiance.</p>
          <br>
          <p style="color:#555;">
            <strong>{e_co}</strong><br>
            {e_addr}<br>
            {e_ph}
          </p>
        </div>
        """
    else:
        subject = f"Invoice {invoice_number} from {company['name']}"
        html_body = f"""
        <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;color:#333;">
          <h2 style="color:#1a3a6b;">Invoice {e_inv}</h2>
          <p>Dear {e_name},</p>
          <p>Please find your invoice attached to this email.</p>
          <p>If you have any questions, feel free to reply to this email or contact us at
             <a href="mailto:{e_mail}">{e_mail}</a>.</p>
          <p>Thank you for your business.</p>
          <br>
          <p style="color:#555;">
            <strong>{e_co}</strong><br>
            {e_addr}<br>
            {e_ph}
          </p>
        </div>
        """

    message = MIMEMultipart()
    message["From"] = formataddr((from_name, gmail_address))
    message["To"] = formataddr((to_name, to_email))
    message["Subject"] = Header(subject, "utf-8")
    message.attach(MIMEText(html_body, "html"))

    attachment = MIMEApplication(pdf_bytes, _subtype="pdf")
    attachment.add_header(
        "Content-Disposition", "attachment", filename=f"Invoice_{invoice_number}.pdf"
    )
    message.attach(attachment)

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(gmail_address, gmail_app_password)
            server.sendmail(gmail_address, [to_email], message.as_string())
        return {
            "success": True,
            "status_code": 250,
            "message": "Email sent",
        }
    except Exception as e:
        return {"success": False, "status_code": 0, "message": str(e)}
