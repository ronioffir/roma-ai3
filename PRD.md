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
test_unit.py         offline unit tests (no network, no secrets)
test_server.py       live smoke test: starts the server over stdio
main.py              L05 legacy test script (not part of the server)
```

- **Language / runtime:** Python 3.12, run with `uv`.
- **SDK:** the official MCP Python SDK, FastMCP API (`mcp` 1.x; pinned `<2`
  because 2.x renamed FastMCP).
- **Transport:** stdio. The server writes nothing to stdout except MCP messages.
- **Time zone:** Asia/Jerusalem for all inputs and outputs. The `tzdata`
  package is a dependency so the zone is also available on Windows.
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

### Error handling and edge cases

Every failure reaches the client as a short error message. Messages never
contain file contents, token values or stack traces, and the server keeps
running.

**Input validation**

| Input | Rule | If broken |
|-------|------|-----------|
| `date` | `YYYY-MM-DD` | Error that names the expected format |
| `start`, `end` | ISO 8601, e.g. `2026-12-01T14:00` | Error that names the expected format |
| `end` | Must be after `start` | Error; nothing is created |
| `duration_minutes` | Greater than 0 | Error |
| `max_results` | 1-50 | Out-of-range values are clamped into the range |
| `days_ahead` | 1-90 | Out-of-range values are clamped into the range |

**Setup and Google errors**

| Situation | What the tool returns |
|-----------|-----------------------|
| `GOOGLE_PRIVATE_DIR` not set, or not an existing folder | Error naming the variable |
| `token.json` missing, unreadable, or not refreshable | Error asking the user to run `authorize.py` |
| Token lacks a needed scope | Error naming the missing permission and `authorize.py` |
| Google answers 401 | "Google rejected the saved token" plus the `authorize.py` hint; the cached token is dropped |
| Google answers 400 / 403 / 404 / 429 | "Could not <action>: <reason> (HTTP <code>)": invalid request, permission or quota, not found, rate limit |

`token.json` is reloaded whenever the file changes, so running `authorize.py`
again takes effect without restarting the server.

**Calendar slot rules (`find_free_slots`)**

- Events marked "free" (`transparency: "transparent"`) do not block time.
- Invitations the user declined do not block time.
- All-day events marked "busy" block the whole day.
- For today's date, times that have already passed are not offered.
- Everything is computed in Asia/Jerusalem, including summer time changes.

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
| `GOOGLE_PRIVATE_DIR` | Yes | Absolute path of the folder holding `client_secret*.json` and `token.json`, for example `/path/to/private-folder`. |

Keep this folder **outside** the `roma-ai3` Git repository (for example
`~/private/gmail-calendar` or `C:\Users\<user>\private\gmail-calendar`), so the
secret files can never be committed by accident.

If the variable is missing or wrong, every tool returns a clear error and the
server keeps running.

## 7. Acceptance criteria

- The server starts with `uv run server.py` and answers MCP `initialize` with
  the name `gmail-calendar`.
- `tools/list` returns exactly the six tools above, each with an English description.
- No Python file in the repository is 150 lines or longer.
- `git status` never shows `token.json` or `client_secret*.json`.
- The offline unit tests and the live smoke test pass (see section 8).

## 8. Verification plan

| Acceptance criterion | How it is checked |
|----------------------|-------------------|
| Server starts and answers `initialize` | `test_server.py` (live, over stdio) |
| Exactly six tools, none that sends or deletes | `test_unit.py` (`ServerTools`) offline, and `test_server.py` live |
| A real tool call works end to end | `test_server.py` calls `list_events(days_ahead=1)` |
| Clear errors for a missing folder or token; token reload | `test_unit.py` (`GoogleAuth`) |
| Email text handling and truncation | `test_unit.py` (`GmailTools`) |
| Free-slot rules, date validation, Asia/Jerusalem | `test_unit.py` (`CalendarTools`) |
| No Python file is 150 lines or longer | `wc -l *.py` |
| No secrets in git | `git status` and `git ls-files` before every commit |
| No send, no delete (manual boundary check) | Ask the agent to send a draft and delete an event; it must do neither and explain that no such tool exists |

Commands:

```bash
uv run python -m unittest -v test_unit.py
GOOGLE_PRIVATE_DIR=/path/to/private-folder uv run test_server.py
```
