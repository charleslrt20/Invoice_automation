import os
import base64
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import (
    Mail, Email, To, Content, Attachment,
    FileContent, FileName, FileType, Disposition,
)


def send_invoice_email(
    to_email: str,
    to_name: str,
    invoice_number: str,
    pdf_bytes: bytes,
    company: dict,
    language: str = "en",
) -> dict:
    api_key = os.environ["SENDGRID_API_KEY"]
    from_email = os.environ["SENDGRID_FROM_EMAIL"]
    from_name = os.environ.get("SENDGRID_FROM_NAME", company["name"])

    if language == "fr":
        subject = f"Facture {invoice_number} de {company['name']}"
        html_body = f"""
        <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;color:#333;">
          <h2 style="color:#1a3a6b;">Facture {invoice_number}</h2>
          <p>Bonjour {to_name},</p>
          <p>Veuillez trouver votre facture en pièce jointe.</p>
          <p>Pour toute question, n'hésitez pas à répondre à cet email ou à nous contacter à
             <a href="mailto:{company['email']}">{company['email']}</a>.</p>
          <p>Merci de votre confiance.</p>
          <br>
          <p style="color:#555;">
            <strong>{company['name']}</strong><br>
            {company['address']}<br>
            {company['phone']}
          </p>
        </div>
        """
    else:
        subject = f"Invoice {invoice_number} from {company['name']}"
        html_body = f"""
        <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;color:#333;">
          <h2 style="color:#1a3a6b;">Invoice {invoice_number}</h2>
          <p>Dear {to_name},</p>
          <p>Please find your invoice attached to this email.</p>
          <p>If you have any questions, feel free to reply to this email or contact us at
             <a href="mailto:{company['email']}">{company['email']}</a>.</p>
          <p>Thank you for your business.</p>
          <br>
          <p style="color:#555;">
            <strong>{company['name']}</strong><br>
            {company['address']}<br>
            {company['phone']}
          </p>
        </div>
        """

    message = Mail(
        from_email=Email(from_email, from_name),
        to_emails=To(to_email, to_name),
        subject=subject,
        html_content=Content("text/html", html_body),
    )

    encoded_pdf = base64.b64encode(pdf_bytes).decode()
    attachment = Attachment(
        file_content=FileContent(encoded_pdf),
        file_name=FileName(f"Invoice_{invoice_number}.pdf"),
        file_type=FileType("application/pdf"),
        disposition=Disposition("attachment"),
    )
    message.attachment = attachment

    try:
        sg = SendGridAPIClient(api_key)
        response = sg.send(message)
        return {
            "success": response.status_code == 202,
            "status_code": response.status_code,
            "message": "Email sent" if response.status_code == 202 else "Unexpected status",
        }
    except Exception as e:
        return {"success": False, "status_code": 0, "message": str(e)}
