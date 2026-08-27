"""
Gmail / Email Integration Tool using Google API
"""
from config.tool_registry import BaseTool, ToolCategory
from config.settings import settings
from loguru import logger
import os
import base64
from email.mime.text import MIMEText

CREDENTIALS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "gmail_credentials")
TOKEN_PATH = os.path.join(CREDENTIALS_DIR, "token.json")
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']


def _get_gmail_service():
    """Build Gmail API service with OAuth2 credentials."""
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    
    os.makedirs(CREDENTIALS_DIR, exist_ok=True)
    creds = None
    
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Cari credentials.json di beberapa lokasi
            creds_file = None
            possible_paths = [
                os.path.join(CREDENTIALS_DIR, "credentials.json"),
                os.path.join(settings.base_dir, "credentials.json"),
                os.path.join(settings.data_dir, "credentials.json"),
            ]
            for p in possible_paths:
                if os.path.exists(p):
                    creds_file = p
                    break
            
            if not creds_file:
                raise Exception(
                    "File credentials.json tidak ditemukan! "
                    "Download dari Google Cloud Console dan simpan di folder data/gmail_credentials/credentials.json"
                )
            
            flow = InstalledAppFlow.from_client_secrets_file(creds_file, SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open(TOKEN_PATH, 'w') as token:
            token.write(creds.to_json())
    
    return build('gmail', 'v1', credentials=creds)


class ReadEmailTool(BaseTool):
    name = "read_email"
    description = "Membaca email terbaru dari Gmail inbox. Params: max_results (opsional, default 5)"
    category = ToolCategory.COMMUNICATION
    
    async def execute(self, max_results: str = "5") -> str:
        try:
            service = _get_gmail_service()
        except Exception as e:
            return str(e)
        
        results = service.users().messages().list(
            userId='me', labelIds=['INBOX'], maxResults=int(max_results)
        ).execute()
        
        messages = results.get('messages', [])
        if not messages:
            return "Inbox kosong. Tidak ada email baru."
        
        email_list = []
        for msg_info in messages:
            msg = service.users().messages().get(userId='me', id=msg_info['id'], format='metadata').execute()
            headers = msg.get('payload', {}).get('headers', [])
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '(No Subject)')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), '(Unknown)')
            snippet = msg.get('snippet', '')
            email_list.append(f"• Dari: {sender}\n  Subjek: {subject}\n  Preview: {snippet[:100]}")
        
        return f"📧 {len(email_list)} email terbaru:\n\n" + "\n\n".join(email_list)


class SendEmailTool(BaseTool):
    name = "send_email"
    description = "Mengirim email melalui Gmail. Params: to, subject, body"
    category = ToolCategory.COMMUNICATION
    
    async def execute(self, to: str, subject: str, body: str) -> str:
        try:
            service = _get_gmail_service()
        except Exception as e:
            return str(e)
        
        message = MIMEText(body)
        message['to'] = to
        message['subject'] = subject
        
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        service.users().messages().send(
            userId='me',
            body={'raw': raw}
        ).execute()
        
        return f"Email berhasil dikirim ke {to} dengan subjek '{subject}'."
