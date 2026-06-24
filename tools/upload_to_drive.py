import io
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

from tools.auth_google import get_google_credentials


def upload_pdf_to_drive(pdf_bytes: bytes, filename: str, folder_id: str) -> dict:
    try:
        creds = get_google_credentials()
        service = build("drive", "v3", credentials=creds)

        media = MediaIoBaseUpload(
            io.BytesIO(pdf_bytes),
            mimetype="application/pdf",
            resumable=False,
        )
        file_metadata = {"name": filename, "parents": [folder_id]}

        uploaded = (
            service.files()
            .create(body=file_metadata, media_body=media, fields="id")
            .execute()
        )

        file_id = uploaded.get("id")
        file_url = f"https://drive.google.com/file/d/{file_id}/view"
        return {"success": True, "file_id": file_id, "file_url": file_url}
    except Exception as e:
        return {"success": False, "file_id": None, "file_url": None, "error": str(e)}
