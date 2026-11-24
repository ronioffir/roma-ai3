# PRD: gmail-calendar MCP server

## 1. Purpose

Give an AI assistant (an MCP client such as Claude) safe, limited access to one
person's Gmail and Google Calendar. The assistant can look things up and prepare
work, but it can never send an email or delete anything. A person always makes
the final move (for example, pressing Send on a draft).

## 2. Goals and non-goals

**Goals**

- Search and read emails.
- Prepare email drafts for a person to review.
- See upcoming calendar events and find free time.
- Add new calendar events.

**Non-goals**

- Sending email.
- Deleting or editing emails, drafts, or calendar events.
- Inviting guests to events.
- Signing in to Google from inside the server.
- Supporting more than one Google account or calendar (only `primary` is used).

## 3. Architecture

```
MCP client (e.g. Claude)
        │  stdio (JSON-RPC over stdin/stdout)
        ▼
server.py            FastMCP server "gmail-calendar": declares the 6 tools
   ├── gmail_tools.py      Gmail logic: search, read, create draft
   ├── calendar_tools.py   Calendar logic: list, free slots, create event
   └── google_auth.py      loads the saved token from GOOGLE_PRIVATE_DIR
                                    │  HTTPS
                                    ▼
                         Gmail API v1 / Calendar API v3

authorize.py         one-time sign-in, run by hand, separate from the server
main.py              last week's test program (not part of the server)
```

- **Language / runtime:** Python 3.12, run with `uv`.
- **SDK:** the official MCP Python SDK, FastMCP API (`mcp` 1.x; pinned `<2`
  because 2.x renamed FastMCP).
- **Transport:** stdio. The server writes nothing to stdout except MCP messages.
- **Time zone:** Asia/Jerusalem for all inputs and outputs.
- **Size rule:** every Python file is under 150 lines.

## 4. Tools

Exactly six tools are exposed.

| # | Tool | Inputs | What it does | Returns |
|---|------|--------|--------------|---------|
| 1 | `search_emails` | `query` (Gmail search syntax), `max_results` (1-50, default 10) | Searches the mailbox | List of `message_id`, `from`, `subject`, `date`, `snippet` |
| 2 | `read_email` | `message_id` | Reads one email | `from`, `to`, `subject`, `date`, `body` (text, max 20,000 chars), `attachments` (names only) |
| 3 | `create_draft` | `to`, `subject`, `body` | Saves a **draft only**; never sends | `draft_id`, `status` |
| 4 | `list_events` | `days_ahead` (1-90, default 7) | Lists events from now until N days ahead | List of `event_id`, `title`, `start`, `end`, `all_day`, `location`, `link` |
| 5 | `find_free_slots` | `date` (YYYY-MM-DD), `duration_minutes` (default 30) | Finds gaps between 08:00 and 20:00 that fit the duration | List of `start`, `end`, `minutes` |
| 6 | `create_event` | `title`, `start`, `end` (ISO 8601), `description` | Adds an event to the primary calendar | `event_id`, `title`, `start`, `end`, `link` |

Details:

- `find_free_slots` treats events marked "free" as not blocking, treats all-day
  "busy" events as blocking the whole day, and never offers times already past.
- `create_event` reads a date-time without an offset as Asia/Jerusalem time,
  rejects an end that is not after the start, and sends no notifications.

## 5. Security boundaries

1. **No send, no delete.** There is no tool that sends an email, deletes an
   email or draft, or deletes or edits a calendar event. The code calls only
   these Google API methods: `messages.list`, `messages.get`, `drafts.create`,
   `events.list`, `events.insert`.
2. **Secrets stay in place.** `client_secret*.json` and `token.json` are read
   only from the folder named by `GOOGLE_PRIVATE_DIR`. They are never copied to
   another location and never printed or logged. Error messages never include
   file contents or token values.
3. **No browser from the server.** If the token is missing, expired beyond
   refresh, or lacks a permission, the tool returns a clear error asking the
   user to run `authorize.py` by hand. The server refreshes an expired access
   token in memory only and does not rewrite `token.json`.
4. **Secrets stay out of git.** `.gitignore` ignores `token.json`,
   `client_secret*.json`, `credentials.json`, `.env`, `__pycache__/`, `.venv/`.
5. **Least-privilege Google permissions (OAuth scopes):**

   | Scope | Needed for |
   |-------|-----------|
   | `gmail.readonly` | `search_emails`, `read_email` |
   | `gmail.compose` | `create_draft` |
   | `calendar.events` | `list_events`, `find_free_slots`, `create_event` |

   Known limit: Google has no "drafts only" permission. `gmail.compose` would
   technically allow sending, and `calendar.events` would allow deleting, so
   the no-send / no-delete guarantee is enforced by this server's code (it
   simply has no such tool), not by Google.

## 6. Environment variables

| Variable | Required | Meaning |
|----------|----------|---------|
| `GOOGLE_PRIVATE_DIR` | Yes | Absolute path of the folder holding `client_secret*.json` and `token.json`. For this project: `/Users/maayanshiri/Desktop/roma-ai3`. |

If the variable is missing or wrong, every tool returns a clear error and the
server keeps running.

## 7. Acceptance criteria

- The server starts with `uv run server.py` and answers MCP `initialize` with
  the name `gmail-calendar`.
- `tools/list` returns exactly the six tools above, each with an English description.
- No file in the repository is 150 lines or longer.
- `git status` never shows `token.json` or `client_secret*.json`.
