from googleapiclient.discovery import build

from tools.auth_google import get_google_credentials


def log_invoice_to_sheets(
    invoice_data: dict,
    subtotal: float,
    vat_amount: float,
    total: float,
    drive_url: str,
    spreadsheet_id: str,
    tab_name: str,
) -> dict:
    try:
        creds = get_google_credentials()
        service = build("sheets", "v4", credentials=creds)

        row = [
            invoice_data.get("invoice_number", ""),
            invoice_data.get("invoice_date", ""),
            invoice_data.get("customer_name", ""),
            invoice_data.get("customer_email", ""),
            invoice_data.get("customer_address", ""),
            round(subtotal, 2),
            invoice_data.get("vat_rate", 0),
            round(vat_amount, 2),
            round(total, 2),
            invoice_data.get("notes", ""),
            drive_url,
            "Sent",
        ]

        result = (
            service.spreadsheets()
            .values()
            .append(
                spreadsheetId=spreadsheet_id,
                range=f"{tab_name}!A:L",
                valueInputOption="USER_ENTERED",
                body={"values": [row]},
            )
            .execute()
        )

        updated_range = result.get("updates", {}).get("updatedRange", "")
        return {"success": True, "updated_range": updated_range}
    except Exception as e:
        return {"success": False, "updated_range": None, "error": str(e)}
