from googleapiclient.discovery import build
from google.oauth2 import service_account
from django.conf import settings

SCOPES = ['https://www.googleapis.com/auth/drive']
SERVICE_ACCOUNT_FILE = settings.GOOGLE_CREDENTIALS_FILE

credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES
)
service = build('drive', 'v3', credentials=credentials)

def find_folder_by_name(name):
    """Search Google Drive for a folder by name."""
    query = f"mimeType='application/vnd.google-apps.folder' and name='{name}' and trashed=false"
    results = service.files().list(q=query, fields="files(id, name)", pageSize=1).execute()
    files = results.get("files", [])
    return files[0] if files else None

def share_drive_file(file_id, email):
    """Share Google Drive file/folder with a user's email."""
    permission = {
        'type': 'user',
        'role': 'reader',
        'emailAddress': email,
    }
    return service.permissions().create(
        fileId=file_id,
        body=permission,
        sendNotificationEmail=False
    ).execute()
