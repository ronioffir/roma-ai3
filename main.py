"""Test program: create a Gmail DRAFT and a Google Calendar event 1 hour from now.

Run with:  uv run main.py
"""

import base64
import sys
from datetime import datetime, timedelta
from email.message import EmailMessage
from pathlib import Path
from zoneinfo import ZoneInfo

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/gmail.compose",  # create drafts (no read of mailbox)
    "https://www.googleapis.com/auth/calendar.events",  # create calendar events
]
TIME_ZONE = "Asia/Jerusalem"

# The client file and token.json live in the same folder as this program.
BASE_DIR = Path(__file__).resolve().parent
TOKEN_FILE = BASE_DIR / "token.json"


def find_client_file() -> Path:
    files = sorted(BASE_DIR.glob("client_secret*.json"))
    if not files:
        sys.exit(f"No client_secret*.json file found in {BASE_DIR}")
    return files[0]


def get_credentials() -> Credentials:
    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if creds and creds.valid:
        return creds
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        # First run: opens the browser once for Google sign-in.
        flow = InstalledAppFlow.from_client_secrets_file(str(find_client_file()), SCOPES)
        creds = flow.run_local_server(port=0)
    TOKEN_FILE.write_text(creds.to_json())
    TOKEN_FILE.chmod(0o600)
    print(f"Token saved to {TOKEN_FILE}")
    return creds


def create_draft(gmail, now: datetime) -> dict:
    me = gmail.users().getProfile(userId="me").execute()["emailAddress"]
    msg = EmailMessage()
    msg["To"] = me
    msg["Subject"] = "Test draft from Python"
    msg.set_content(f"This draft was created by the test program at {now:%Y-%m-%d %H:%M}.")
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    return gmail.users().drafts().create(userId="me", body={"message": {"raw": raw}}).execute()


def create_event(calendar, now: datetime) -> dict:
    start = now + timedelta(hours=1)
    end = start + timedelta(hours=1)
    event = {
        "summary": "Test event from Python",
        "description": "Created by the test program.",
        "start": {"dateTime": start.isoformat(), "timeZone": TIME_ZONE},
        "end": {"dateTime": end.isoformat(), "timeZone": TIME_ZONE},
    }
    return calendar.events().insert(calendarId="primary", body=event).execute()


def main() -> None:
    creds = get_credentials()
    now = datetime.now(ZoneInfo(TIME_ZONE)).replace(second=0, microsecond=0)

    gmail = build("gmail", "v1", credentials=creds)
    draft = create_draft(gmail, now)
    print(f"Gmail draft created (id: {draft['id']}) - check Gmail > Drafts. Nothing was sent.")

    calendar = build("calendar", "v3", credentials=creds)
    event = create_event(calendar, now)
    start = datetime.fromisoformat(event["start"]["dateTime"])
    print(f"Calendar event created at {start:%Y-%m-%d %H:%M} ({TIME_ZONE}): {event['htmlLink']}")


if __name__ == "__main__":
    main()
