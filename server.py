"""gmail-calendar: an MCP server for Gmail and Google Calendar (stdio transport).

Run with:  GOOGLE_PRIVATE_DIR=/path/to/private/folder uv run server.py

Exactly six tools are exposed. None of them sends or deletes anything.
"""

from mcp.server.fastmcp import FastMCP

import calendar_tools
import gmail_tools

mcp = FastMCP("gmail-calendar")


@mcp.tool()
def search_emails(query: str, max_results: int = 10) -> list[dict]:
    """Search Gmail with a Gmail search query (e.g. "from:dana is:unread").

    Returns up to max_results (1-50) messages with id, sender, subject, date and snippet.
    """
    return gmail_tools.search_emails(query, max_results)


@mcp.tool()
def read_email(message_id: str) -> dict:
    """Read one email by its message_id (from search_emails).

    Returns the sender, recipient, subject, date, text body and attachment names.
    """
    return gmail_tools.read_email(message_id)


@mcp.tool()
def create_draft(to: str, subject: str, body: str) -> dict:
    """Create a Gmail DRAFT only. The email is saved in Drafts and is never sent."""
    return gmail_tools.create_draft(to, subject, body)


@mcp.tool()
def list_events(days_ahead: int = 7) -> list[dict]:
    """List Google Calendar events from now until days_ahead days from now (1-90).

    Times are in the Asia/Jerusalem time zone.
    """
    return calendar_tools.list_events(days_ahead)


@mcp.tool()
def find_free_slots(date: str, duration_minutes: int = 30) -> list[dict]:
    """Find free time slots on a date (YYYY-MM-DD) that fit duration_minutes.

    Searches between 08:00 and 20:00, Asia/Jerusalem time.
    """
    return calendar_tools.find_free_slots(date, duration_minutes)


@mcp.tool()
def create_event(title: str, start: str, end: str, description: str = "") -> dict:
    """Create a Google Calendar event. No invitations are sent.

    start and end are ISO 8601 date-times (e.g. 2026-12-01T14:00) in Asia/Jerusalem time.
    """
    return calendar_tools.create_event(title, start, end, description)


if __name__ == "__main__":
    mcp.run(transport="stdio")
