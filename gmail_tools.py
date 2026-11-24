"""Gmail operations: search, read, and create a draft. Nothing here sends or deletes."""

import base64
import html
import re
from email.message import EmailMessage

from google_auth import GMAIL_COMPOSE, GMAIL_READ, gmail, require_scope

MAX_BODY_CHARS = 20000


def _headers(message: dict) -> dict:
    return {h["name"].lower(): h["value"] for h in message.get("payload", {}).get("headers", [])}


def _decode(data: str) -> str:
    return base64.urlsafe_b64decode(data.encode()).decode("utf-8", errors="replace")


def _strip_html(text: str) -> str:
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<br\s*/?>|</p>|</div>", "\n", text, flags=re.I)
    text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    return re.sub(r"[ \t]+", " ", text).strip()


def _body_text(payload: dict) -> str:
    """Return the readable text of a message, preferring plain text over HTML."""
    plain, rich = [], []

    def walk(part: dict) -> None:
        data = part.get("body", {}).get("data")
        if data and not part.get("filename"):
            if part.get("mimeType") == "text/plain":
                plain.append(_decode(data))
            elif part.get("mimeType") == "text/html":
                rich.append(_decode(data))
        for child in part.get("parts", []):
            walk(child)

    walk(payload)
    if plain:
        return "\n".join(plain).strip()
    return _strip_html("\n".join(rich))


def _attachment_names(payload: dict) -> list[str]:
    names = [payload["filename"]] if payload.get("filename") else []
    for child in payload.get("parts", []):
        names.extend(_attachment_names(child))
    return names


def search_emails(query: str, max_results: int = 10) -> list[dict]:
    require_scope(GMAIL_READ)
    limit = max(1, min(int(max_results), 50))
    found = gmail().users().messages().list(userId="me", q=query, maxResults=limit).execute()
    results = []
    for item in found.get("messages", []):
        message = (
            gmail()
            .users()
            .messages()
            .get(
                userId="me",
                id=item["id"],
                format="metadata",
                metadataHeaders=["From", "Subject", "Date"],
            )
            .execute()
        )
        headers = _headers(message)
        results.append(
            {
                "message_id": message["id"],
                "from": headers.get("from", ""),
                "subject": headers.get("subject", ""),
                "date": headers.get("date", ""),
                "snippet": message.get("snippet", ""),
            }
        )
    return results


def read_email(message_id: str) -> dict:
    require_scope(GMAIL_READ)
    message = gmail().users().messages().get(userId="me", id=message_id, format="full").execute()
    headers = _headers(message)
    body = _body_text(message.get("payload", {}))
    return {
        "message_id": message["id"],
        "from": headers.get("from", ""),
        "to": headers.get("to", ""),
        "subject": headers.get("subject", ""),
        "date": headers.get("date", ""),
        "body": body[:MAX_BODY_CHARS],
        "body_truncated": len(body) > MAX_BODY_CHARS,
        "attachments": _attachment_names(message.get("payload", {})),
    }


def create_draft(to: str, subject: str, body: str) -> dict:
    require_scope(GMAIL_COMPOSE)
    message = EmailMessage()
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    draft = gmail().users().drafts().create(userId="me", body={"message": {"raw": raw}}).execute()
    return {
        "draft_id": draft["id"],
        "status": "Draft saved in Gmail > Drafts. It was NOT sent.",
    }
