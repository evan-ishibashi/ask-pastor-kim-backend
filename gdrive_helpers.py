from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

# Authenticate and initialize Google Drive
def authenticate_drive():
    gauth = GoogleAuth()
    gauth.LoadCredentialsFile("mycreds.txt")

    if gauth.credentials is None:
        # Authenticate if they're not there
        gauth.LocalWebserverAuth()
    elif gauth.access_token_expired:
        # Refresh them if expired
        gauth.Refresh()
    else:
        # Initialize the saved creds
        gauth.Authorize()

    # Save the current credentials to a file
    gauth.SaveCredentialsFile("mycreds.txt")

    return GoogleDrive(gauth)

# Download a file from Google Drive by file ID
def download_file_from_drive(drive, file_id, destination_path):
    file = drive.CreateFile({'id': file_id})
    file.FetchMetadata()
    file.GetContentFile(destination_path)
    print(f"✅ Downloaded: {destination_path}")

# Upload (or replace) a file to Google Drive by file ID
def upload_file_to_drive(drive, local_path, file_id):
    file = drive.CreateFile({'id': file_id})
    file.SetContentFile(local_path)
    file.Upload()
    print(f"☁️ Uploaded: {local_path}")