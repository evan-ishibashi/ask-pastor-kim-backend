from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
import io


def authenticate_drive():
    """Authenticate and return a Drive API client."""
    SERVICE_ACCOUNT_FILE = 'service_account_key.json'
    SCOPES = ['https://www.googleapis.com/auth/drive']

    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)

    return build('drive', 'v3', credentials=credentials)


def download_file_from_drive(service, file_id, destination_path):
    """Download a file from Google Drive."""
    request = service.files().get_media(fileId=file_id)
    fh = io.FileIO(destination_path, 'wb')
    downloader = MediaIoBaseDownload(fh, request)

    done = False
    while not done:
        status, done = downloader.next_chunk()
        print(f"🔽 Download progress: {int(status.progress() * 100)}%")
    print(f"✅ File downloaded to {destination_path}")


def upload_file_to_drive(service, local_path, file_id, mime_type='application/json'):
    """Update an existing file on Google Drive by overwriting it."""
    media = MediaFileUpload(local_path, mimetype=mime_type)
    updated_file = service.files().update(fileId=file_id, media_body=media).execute()
    print(f"☁️ File uploaded: {updated_file.get('name')} (ID: {file_id})")
