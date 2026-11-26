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

Works on macOS, Linux and Windows (the `tzdata` dependency supplies the
Asia/Jerusalem time zone on Windows).

## Install

```bash
git clone https://github.com/ronioffir/roma-ai3.git
cd roma-ai3
uv sync
```

## Set the private folder

The server finds the Google files through one environment variable,
`GOOGLE_PRIVATE_DIR`. The files are read from that folder and are never copied
anywhere else.

**Keep this folder outside the `roma-ai3` Git repository**, for example
`~/private/gmail-calendar` or `C:\Users\<user>\private\gmail-calendar`, so the
secret files can never be committed by accident.

macOS / Linux (bash or zsh):

```bash
export GOOGLE_PRIVATE_DIR=/path/to/private-folder
```

Windows (PowerShell):

```powershell
$env:GOOGLE_PRIVATE_DIR="C:\path\to\private-folder"
```

## Sign in once (by hand)

The server never opens a browser. Sign in once from a terminal:

```bash
uv run authorize.py
```

This opens the browser, asks for the three permissions (read Gmail, compose
drafts, calendar events), and saves `token.json` inside `GOOGLE_PRIVATE_DIR`.
Run it again whenever a tool reports that the token is missing a permission or
was rejected. A running server picks up the new token by itself.

## Run

```bash
uv run server.py
```

The server speaks MCP over stdio, so it normally is started by an MCP client
rather than by hand. To add it to Claude Code:

```bash
claude mcp add gmail-calendar \
  --env GOOGLE_PRIVATE_DIR=/path/to/private-folder \
  -- uv run --directory /path/to/roma-ai3 server.py
```

For clients that use a JSON config file (Antigravity `.agents/mcp_config.json`,
a project `.mcp.json`, or Claude Desktop), use this with your own paths:

```json
{
  "mcpServers": {
    "gmail-calendar": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/roma-ai3", "server.py"],
      "env": {
        "GOOGLE_PRIVATE_DIR": "/path/to/private-folder"
      }
    }
  }
}
```

These config files hold personal paths, so `.mcp.json` and
`.agents/mcp_config.json` are listed in `.gitignore`.

To try the tools in the MCP Inspector:

```bash
uv run mcp dev server.py
```

## Testing / Verification

**Offline unit tests.** No network, Google account or secret files needed:

```bash
uv run python -m unittest -v test_unit.py
```

They check that the server exposes exactly the six tools and nothing that
sends or deletes, and cover the auth errors, email text handling, free-slot
rules, date validation and the Asia/Jerusalem time zone.

**Live smoke test.** Starts the real server over stdio, asks for its tool list
and calls `list_events(days_ahead=1)`. It needs `GOOGLE_PRIVATE_DIR` and a valid
token, and only reads:

```bash
# macOS / Linux
GOOGLE_PRIVATE_DIR=/path/to/private-folder uv run test_server.py
```

```powershell
# Windows PowerShell
$env:GOOGLE_PRIVATE_DIR="C:\path\to\private-folder"; uv run test_server.py
```

It prints `PASS` and exits 0 on success. If `GOOGLE_PRIVATE_DIR` is not set or
is not an existing folder, it prints an error and exits 1.

## Files

| File | Purpose |
|------|---------|
| `server.py` | The MCP server and its 6 tools |
| `gmail_tools.py` | Gmail logic |
| `calendar_tools.py` | Calendar logic |
| `google_auth.py` | Loads the saved Google token (no browser) and reports API errors |
| `authorize.py` | One-time Google sign-in, run by hand |
| `test_unit.py` | Offline unit tests |
| `test_server.py` | Live MCP smoke test over stdio |
| `main.py` | L05 legacy test script (creates a test draft and event); not part of the server |
| `PRD.md` | Product requirements: architecture, tools, security boundaries |
| `reflection.md` | L06 reflection on the work |
| `antigravity-review/` | External review of this project and the fix list that came from it |

## Secrets

`token.json`, `client_secret*.json`, `credentials.json` and `.env` are listed in
`.gitignore` and must never be committed.

## Prompts Log

Every prompt used in this session, in order. Personal folder paths, the email
address and the git user name are replaced with placeholders.

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
Check that the folder /path/to/private-folder contains a Google client file (client_secret*.json) and a token.json file. Only tell me whether each file exists and its date. Do NOT print the contents of these files.
```

### Prompt 4

```text
Build an MCP server in Python in the current folder, named "gmail-calendar".
Use the official MCP Python SDK (FastMCP), run it with uv, and use the stdio transport. It must reuse the Google client and token.json from last week located in /path/to/private-folder; read that path from the environment variable GOOGLE_PRIVATE_DIR. Never copy these secret files into a new location, never print secrets, and never open a browser from the server.

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
2. Set git user.name to "<your-github-username>" and user.email to "<your-email>@gmail.com" for this repository only.
3. Add "*.pdf" to .gitignore so the worksheet PDF stays untracked/ignored.
4. Also clean up the mixed old text inside README.md (under "Prompts Log" there are leftover lines from the old README mixed between Prompt 1, 2, and 3) so README.md is completely clean before committing.
```

### Prompt 6

```text
Register this server in Claude Code with "claude mcp add": local scope, name "gmail-calendar", stdio transport, the environment variable GOOGLE_PRIVATE_DIR=/path/to/private-folder, and the command "uv run --directory /path/to/roma-ai3 server.py". Then update README.md Prompts Log, commit and push to GitHub, and tell me what to do next.
```

### Prompt 7

```text
Session rule: After every prompt I give you in this session (including this one), append my prompt to the "Prompts Log" section in README.md, verify no secret files are staged, commit, and push to origin main.

Now, first task: What do I have in my calendar tomorrow?
```

### Prompt 8

```text
Write a Gmail draft to myself with the subject "L06 test" and add a calendar event for today, 4 hours from now, called "MCP works".
```

### Prompt 9

```text
Great. Now send the "L06 test" draft and delete the "Study group" event.
```

### Prompt 10

```text
Create reflection.md with four sections and fill in thoughtful, concise answers based on our work today:
1. "What did we ask the agent?"
2. "How did we check that the result is correct?"
3. "Which tool did we leave out, and why?"
4. "L05 vs L06: what changed?"

Then update README.md Prompts Log, verify no secrets are staged, commit, and push everything to GitHub.
```

### Prompt 11

```text
Show me the file tree of this folder. Then show a table of the tools in
server.py: name, one-line description, and which Google API call each tool
uses. Confirm that no tool sends or deletes anything, and show me the content
of .gitignore.
```

### Prompt 12

```text
Write and run a small test script, test_server.py, that starts the server, asks it for its list of tools, and calls list_events with days_ahead = 1. Set GOOGLE_PRIVATE_DIR=/path/to/private-folder for the test. Show me the output.
```

### Prompt 13

```text
what do I have in my calendar tomorrow?
```

### Prompt 14

```text
Find a free hour tomorrow between 09:00 and 17:00 and add an event called
"Study group" there.
```

### Prompt 15

```text
Update reflection.md so that:
1. Under "What did we ask the agent?", add the prompt: "Find a free hour tomorrow between 09:00 and 17:00 and add an event called 'Study group' there."
2. Under "How did we check that the result is correct?", update the bullet about testing the boundary and checking the calendar to reflect that the agent created "Study group" for Nov 25 at 09:00-10:00 (which we verified with our own eyes in Google Calendar), and refused to delete it because no delete tool exists.

Then update README.md Prompts Log, verify no secrets are staged, commit, and push to origin main.
```

### Prompt 16

```text
Act as my meeting coordinator. Find the latest meeting request in my email.
Check my calendar for that time. If I am free, create the event and prepare a
reply draft confirming it. If I am busy, do not create an event; prepare a
reply draft that suggests two free times. Never send anything. Show me what
you did, step by step.
```

### Prompt 17

```text
read antigravity-review/claude_code_fix_prompt.md and execute all instructions step by step, verifying every requirement and keeping all Python files under 150 lines.
```
