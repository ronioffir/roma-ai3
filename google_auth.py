"""Google credentials for the gmail-calendar MCP server.

The secret files (client_secret*.json and token.json) stay in the private folder
named by the GOOGLE_PRIVATE_DIR environment variable. This module only reads
them from there: it never copies them, never prints them, and never opens a
browser. If the token is missing or lacks a scope, it raises a clear error that
tells the user to run authorize.py by hand.
"""

import os
from functools import lru_cache
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

TIME_ZONE = "Asia/Jerusalem"

GMAIL_READ = "https://www.googleapis.com/auth/gmail.readonly"
GMAIL_COMPOSE = "https://www.googleapis.com/auth/gmail.compose"
CALENDAR_EVENTS = "https://www.googleapis.com/auth/calendar.events"
SCOPES = [GMAIL_READ, GMAIL_COMPOSE, CALENDAR_EVENTS]

REAUTH_HINT = "Run authorize.py once in a terminal to sign in with Google (see README.md)."


class GoogleAuthError(RuntimeError):
    """Raised when the saved Google token cannot be used."""


def private_dir() -> Path:
    """Return the folder that holds the Google secret files."""
    value = os.environ.get("GOOGLE_PRIVATE_DIR")
    if not value:
        raise GoogleAuthError("The GOOGLE_PRIVATE_DIR environment variable is not set.")
    folder = Path(value).expanduser()
    if not folder.is_dir():
        raise GoogleAuthError("GOOGLE_PRIVATE_DIR does not point to an existing folder.")
    return folder


def token_file() -> Path:
    return private_dir() / "token.json"


def client_file() -> Path:
    files = sorted(private_dir().glob("client_secret*.json"))
    if not files:
        raise GoogleAuthError("No client_secret*.json file found in GOOGLE_PRIVATE_DIR.")
    return files[0]


@lru_cache(maxsize=1)
def get_credentials() -> Credentials:
    """Load the saved token. Refreshes it in memory if expired; no browser."""
    path = token_file()
    if not path.exists():
        raise GoogleAuthError(f"token.json was not found in GOOGLE_PRIVATE_DIR. {REAUTH_HINT}")
    creds = Credentials.from_authorized_user_file(str(path))
    if not creds.valid:
        if not creds.refresh_token:
            raise GoogleAuthError(f"The saved Google token cannot be refreshed. {REAUTH_HINT}")
        try:
            creds.refresh(Request())
        except Exception as exc:  # expired or revoked refresh token
            raise GoogleAuthError(f"Google rejected the saved token. {REAUTH_HINT}") from exc
    return creds


def require_scope(scope: str) -> None:
    """Fail with a clear message if the saved token was not granted `scope`."""
    granted = get_credentials().scopes or []
    if scope not in granted:
        name = scope.rsplit("/", 1)[-1]
        raise GoogleAuthError(f"The saved Google token lacks the '{name}' permission. {REAUTH_HINT}")


@lru_cache(maxsize=None)
def _service(name: str, version: str):
    return build(name, version, credentials=get_credentials(), cache_discovery=False)


def gmail():
    return _service("gmail", "v1")


def calendar():
    return _service("calendar", "v3")
