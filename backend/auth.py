import json
import os
from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

BASE_DIR = Path(__file__).resolve().parent

SCOPES = ["https://www.googleapis.com/auth/calendar"]
DEFAULT_CREDENTIALS_PATH = BASE_DIR / "credentials.json"
DEFAULT_TOKEN_PATH = BASE_DIR / "token.json"


def _load_credentials(token_path: Path) -> Optional[Credentials]:
    if not token_path.exists():
        return None
    return Credentials.from_authorized_user_file(str(token_path), SCOPES)


def _save_credentials(token_path: Path, credentials: Credentials) -> None:
    token_path.write_text(credentials.to_json())


def get_calendar_service():
    credentials_path = Path(os.environ.get("CUMO_GOOGLE_CREDENTIALS", DEFAULT_CREDENTIALS_PATH))
    token_path = Path(os.environ.get("CUMO_GOOGLE_TOKEN", DEFAULT_TOKEN_PATH))

    creds = _load_credentials(token_path)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        _save_credentials(token_path, creds)

    if not creds or not creds.valid:
        if not credentials_path.exists():
            raise FileNotFoundError(
                f"Google OAuth credentials not found at {credentials_path}. "
                "Provide credentials.json or set CUMO_GOOGLE_CREDENTIALS."
            )

        flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
        creds = flow.run_local_server(port=0)
        _save_credentials(token_path, creds)

    return build("calendar", "v3", credentials=creds)

