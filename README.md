# gmail-calendar MCP server

An MCP server (Python, FastMCP, stdio) that lets an AI assistant work with your
Gmail and Google Calendar. It can search and read emails, create **drafts**,
list events, find free time, and create events. It has **no tool that sends or
deletes anything**. Time zone: Asia/Jerusalem.

See [PRD.md](PRD.md) for the full design and security boundaries.

## Tools

| Tool | What it does |
|------|--------------|
| `search_emails(query, max_results)` | Search Gmail with a Gmail search query |
| `read_email(message_id)` | Read one email |
| `create_draft(to, subject, body)` | Create a DRAFT only (never sent) |
| `list_events(days_ahead)` | List upcoming calendar events |
| `find_free_slots(date, duration_minutes)` | Find free time on a date (08:00-20:00) |
| `create_event(title, start, end, description)` | Create a calendar event |

## Requirements

- [uv](https://docs.astral.sh/uv/) (installs Python and the dependencies automatically)
- A private folder holding your Google OAuth Desktop client file
  (`client_secret*.json`) and `token.json`
- Gmail API and Google Calendar API enabled in the Google Cloud project

## Install

```bash
git clone https://github.com/ronioffir/roma-ai3.git
cd roma-ai3
uv sync
```

## Set the private folder

The server finds the Google files through one environment variable. The files
are read from that folder and are never copied anywhere else.

```bash
export GOOGLE_PRIVATE_DIR=/Users/maayanshiri/Desktop/roma-ai3
```

## Sign in once (by hand)

The server never opens a browser. Sign in once from a terminal:

```bash
uv run authorize.py
```

This opens the browser, asks for the three permissions (read Gmail, compose
drafts, calendar events), and saves `token.json` inside `GOOGLE_PRIVATE_DIR`.
Run it again whenever a tool reports that the token is missing a permission or
was rejected.

## Run

```bash
uv run server.py
```

The server speaks MCP over stdio, so it normally is started by an MCP client
rather than by hand. To add it to Claude Code:

```bash
claude mcp add gmail-calendar \
  --env GOOGLE_PRIVATE_DIR=/Users/maayanshiri/Desktop/roma-ai3 \
  -- uv run --directory /Users/maayanshiri/Desktop/roma-ai3 server.py
```

To try the tools in the MCP Inspector:

```bash
uv run mcp dev server.py
```

## Files

| File | Purpose |
|------|---------|
| `server.py` | The MCP server and its 6 tools |
| `gmail_tools.py` | Gmail logic |
| `calendar_tools.py` | Calendar logic |
| `google_auth.py` | Loads the saved Google token (no browser) |
| `authorize.py` | One-time Google sign-in, run by hand |
| `main.py` | Last week's test program (creates a test draft and event) |

## Secrets

`token.json`, `client_secret*.json`, `credentials.json` and `.env` are listed in
`.gitignore` and must never be committed.

## Prompts Log

Every prompt used in this session, in order.

### Prompt 1

```text
uv run main.py
```

### Prompt 2

```text
In one sentence: which folder are you working in?
```

### Prompt 3

```text
Check that the folder /Users/maayanshiri/Desktop/roma-ai3 contains a Google client file (client_secret*.json) and a token.json file. Only tell me whether each file exists and its date. Do NOT print the contents of these files.
```

### Prompt 4

```text
Build an MCP server in Python in the current folder, named "gmail-calendar".
Use the official MCP Python SDK (FastMCP), run it with uv, and use the stdio transport. It must reuse the Google client and token.json from last week located in /Users/maayanshiri/Desktop/roma-ai3; read that path from the environment variable GOOGLE_PRIVATE_DIR. Never copy these secret files into a new location, never print secrets, and never open a browser from the server.

Expose exactly these 6 tools, each with a short, clear English description:
1. search_emails(query, max_results)
2. read_email(message_id)
3. create_draft(to, subject, body) - creates a DRAFT only
4. list_events(days_ahead)
5. find_free_slots(date, duration_minutes)
6. create_event(title, start, end, description)

There must be NO tool that sends or deletes anything. Time zone: Asia/Jerusalem. Keep each Python file under 150 lines.

Documentation & Git Setup:
1. Create a strict .gitignore file that ignores token.json, client_secret*.json, credentials.json, .env, __pycache__/, and .venv/.
2. Create a detailed PRD.md (Product Requirements Document) describing the server's architecture, the 6 tools, security boundaries (no send/delete), and environment variables.
3. Create a clear README.md that explains how to install and run the server, and include a section at the bottom titled "Prompts Log" where we will document every prompt used in this session (start by adding the prompts used so far).
4. Initialize git (if not already initialized), connect the remote origin to https://github.com/ronioffir/roma-ai3.git, show me `git status` to verify that NO secret files (token.json, client_secret*.json) are staged, and only after my confirmation, commit and push to main.

Rule for the rest of this session: After every prompt I give you from now on, update the "Prompts Log" section in README.md with the prompt I used, and commit and push the changes to GitHub (always verifying no secrets are included).
```

### Prompt 5

```text
1. Confirmed, please commit and push the 12 staged files to main.
2. Set git user.name to "maayanshiri" and user.email to "maayanshiri2002@gmail.com" for this repository only.
3. Add "*.pdf" to .gitignore so the worksheet PDF stays untracked/ignored.
4. Also clean up the mixed old text inside README.md (under "Prompts Log" there are leftover lines from the old README mixed between Prompt 1, 2, and 3) so README.md is completely clean before committing.
```

### Prompt 6

```text
Register this server in Claude Code with "claude mcp add": local scope, name "gmail-calendar", stdio transport, the environment variable GOOGLE_PRIVATE_DIR=/Users/maayanshiri/Desktop/roma-ai3, and the command "uv run --directory /Users/maayanshiri/Desktop/roma-ai3 server.py". Then update README.md Prompts Log, commit and push to GitHub, and tell me what to do next.
```

### Prompt 7

```text
Session rule: After every prompt I give you in this session (including this one), append my prompt to the "Prompts Log" section in README.md, verify no secret files are staged, commit, and push to origin main.

Now, first task: What do I have in my calendar tomorrow?
```
