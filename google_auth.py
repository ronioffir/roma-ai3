"""Google credentials for the gmail-calendar MCP server.

The secret files (client_secret*.json and token.json) stay in the private folder
named by the GOOGLE_PRIVATE_DIR environment variable. This module only reads
them from there: it never copies them, never prints them, and never opens a
browser. If the token is missing or lacks a scope, it raises a clear error that
tells the user to run authorize.py by hand.
"""

import os
from pathlib import Path

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

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


_cache: dict = {}  # holds the loaded token and API clients for one version of token.json

_HTTP_HINTS = {
    400: "the request was not valid (check the query, id, or dates)",
    401: f"Google rejected the saved token. {REAUTH_HINT}",
    403: "Google refused the request (missing permission or quota exceeded)",
    404: "the item was not found",
    429: "the Google rate limit was reached; try again in a minute",
}


def reset_cache() -> None:
    """Forget the loaded token and API clients so the next call reloads them."""
    _cache.clear()


def get_credentials() -> Credentials:
    """Load the saved token. Refreshes it in memory if expired; no browser.

    The token is reloaded whenever token.json changes on disk, so running
    authorize.py again takes effect without restarting the server.
    """
    path = token_file()
    if not path.exists():
        raise GoogleAuthError(f"token.json was not found in GOOGLE_PRIVATE_DIR. {REAUTH_HINT}")
    stamp = path.stat().st_mtime_ns
    if _cache.get("stamp") != stamp:
        reset_cache()
        try:
            creds = Credentials.from_authorized_user_file(str(path))
        except ValueError:  # the message could quote the file, so it is not passed on
            raise GoogleAuthError(f"token.json in GOOGLE_PRIVATE_DIR is not valid. {REAUTH_HINT}") from None
        _cache.update(stamp=stamp, creds=creds)
    creds = _cache["creds"]
    if not creds.valid:
        if not creds.refresh_token:
            raise GoogleAuthError(f"The saved Google token cannot be refreshed. {REAUTH_HINT}")
        try:
            creds.refresh(Request())
        except Exception:  # expired or revoked refresh token, or no network
            reset_cache()
            raise GoogleAuthError(f"Google rejected the saved token. {REAUTH_HINT}") from None
    return creds


def require_scope(scope: str) -> None:
    """Fail with a clear message if the saved token was not granted `scope`."""
    granted = get_credentials().scopes or []
    if scope not in granted:
        name = scope.rsplit("/", 1)[-1]
        raise GoogleAuthError(f"The saved Google token lacks the '{name}' permission. {REAUTH_HINT}")


def _service(name: str, version: str):
    creds = get_credentials()  # also drops stale clients if token.json changed
    if name not in _cache:
        _cache[name] = build(name, version, credentials=creds, cache_discovery=False)
    return _cache[name]


def gmail():
    return _service("gmail", "v1")


def calendar():
    return _service("calendar", "v3")


def execute(request, action: str):
    """Run a Google API request; turn failures into short errors with no secrets in them."""
    try:
        return request.execute()
    except RefreshError:
        reset_cache()
        raise GoogleAuthError(f"Google rejected the saved token. {REAUTH_HINT}") from None
    except HttpError as exc:
        status = int(exc.resp.status)
        if status == 401:
            reset_cache()
        hint = _HTTP_HINTS.get(status, "Google returned an error; try again later")
        raise RuntimeError(f"Could not {action}: {hint} (HTTP {status}).") from None
