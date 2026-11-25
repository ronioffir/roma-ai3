# Critical L06 Audit & 100/100 Readiness Review: `roma-ai3`

**Repository:** `git@github.com:ronioffir/roma-ai3.git` (branch `main`, audited at commit `d0d76eb`)  
**Assignment:** L06 — MCP Server for Gmail and Calendar (Vibe Coding / AI Agents, Rami / Dr. Yoram Segal slides 21–37)  
**Assessment Method:** Full static inspection of all 14 tracked files, git history (`git log`, `git ls-files`, `git status`), and lockfile (`uv.lock`). *(Note: Runtime execution via `uv` was not performed on this Windows host because `uv` is not installed here and no Google OAuth credentials were present.)*

---

## Executive Summary & Grade Estimate

**Estimated Score Toward Rami's 100/100 Bar: `90 / 100` (Strong A- / Very close to 100)**

This is an impressively clean, disciplined, and thoughtful submission. The Python codebase is concise (every `.py` file is strictly under 135 lines), cleanly modularized, free of stdout pollution, enforces `Asia/Jerusalem` throughout, exposes the exact 6 required tools with zero send/delete capabilities, and includes both a genuine `PRD.md` and an unusually perceptive `reflection.md` (including a self-correction commit `9c744bc` clarifying that code—not OAuth scopes—enforces the no-send/no-delete guarantee).

However, **it does not yet deserve 100/100** due to several concrete portability, privacy, and cross-platform defects—most notably a **hardcoded personal macOS directory path in `test_server.py` (line 15)** that overrides `GOOGLE_PRIVATE_DIR` and breaks execution on any other machine, personal path/email leaks in `README.md` and `PRD.md`, a missing `tzdata` dependency for Windows `ZoneInfo("Asia/Jerusalem")`, minor doc inaccuracies, and missing offline unit tests.

---

## 1. Secret Safety & Repository Hygiene

### Tracked Files (`git ls-files`)
14 files are tracked on `main`:
`.gitignore`, `.python-version`, `PRD.md`, `README.md`, `authorize.py`, `calendar_tools.py`, `gmail_tools.py`, `google_auth.py`, `main.py`, `pyproject.toml`, `reflection.md`, `server.py`, `test_server.py`, `uv.lock`.

- **No OAuth/secret files tracked:** `token.json`, `client_secret*.json`, `credentials.json`, and `.env` are absent from the repository and git history inspected.
- **`.gitignore` coverage (18 lines):** Ignores `token.json`, `token*.json`, `client_secret*.json`, `credentials.json`, `.env`, `.env.*`, `__pycache__/`, `*.pyc`, `.venv/`, `.DS_Store`, `*.pdf`.
  - **Minor gaps:** Missing common test/lint/IDE/Windows/MCP local config patterns such as `.pytest_cache/`, `.ruff_cache/`, `*.egg-info/`, `dist/`, `build/`, `Thumbs.db`, `.vscode/`, `.idea/`, and `.mcp.json` / `.agents/mcp_config.json` (if created locally with machine paths).

### Personal Information & Path Leaks Found
1. **`test_server.py` (lines 15 & 30):** Hardcodes `PRIVATE_DIR = "/Users/<user>/Desktop/roma-ai3"` and passes `env={**os.environ, "GOOGLE_PRIVATE_DIR": PRIVATE_DIR}`, overwriting any `GOOGLE_PRIVATE_DIR` the grader sets.
2. **`README.md` (lines 42, 69–70, 114, 121, 154, 201) & `PRD.md` (line 105):** Hardcode the personal local macOS path `/Users/<user>/Desktop/roma-ai3` in setup commands, Claude registration instructions, PRD env table, and the Prompts Log.
3. **`README.md` (line 146, Prompt 5):** Exposes a personal email address (`<personal-email>@gmail.com`) inside the committed `git config` prompt.
4. **Operational security smell:** The path `/Users/<user>/Desktop/roma-ai3` indicates `GOOGLE_PRIVATE_DIR` pointed to the repository directory itself rather than a separate folder outside the Git working tree. Even with `.gitignore`, keeping secrets in a completely separate folder (e.g., `~/.secrets/gmail-calendar`) is much safer against accidental `git add -f` or archive leaks.

---

## 2. Audit Against L06 Assignment Requirements

### A. MCP Server Architecture & Setup
| Requirement | Status | Evidence & Notes |
|---|---|---|
| Official MCP Python SDK (`FastMCP`) | Pass | `pyproject.toml` pins `mcp[cli]<2`; `server.py` uses `from mcp.server.fastmcp import FastMCP` and `FastMCP("gmail-calendar")`. |
| Runnable with `uv` | Pass | `pyproject.toml`, `.python-version` (`3.12`), and `uv.lock` are present; documented with `uv run server.py`. |
| `stdio` transport & no stdout pollution | Pass | `server.py` calls `mcp.run(transport="stdio")`. Zero `print()` calls in `server.py`, `gmail_tools.py`, `calendar_tools.py`, or `google_auth.py`. |
| Reads `GOOGLE_PRIVATE_DIR` (folder, not file) | Pass | `google_auth.py` `private_dir()` reads `os.environ.get("GOOGLE_PRIVATE_DIR")`, expands `~`, checks `folder.is_dir()`, and resolves `token.json` and `client_secret*.json` inside it. |
| Reuses secrets in place; never copies or opens browser from server | Pass | `google_auth.py` only reads `token.json` and refreshes in memory; `InstalledAppFlow` is isolated in standalone `authorize.py`. |
| Enforces `Asia/Jerusalem` time zone | Partial Pass (OS caveat) | `calendar_tools.py` uses `ZoneInfo("Asia/Jerusalem")` for parsing, naive datetime localization, `events.list(timeZone=...)`, and `events.insert`. **Defect:** `tzdata` is missing from `pyproject.toml` and `uv.lock`, so `ZoneInfo("Asia/Jerusalem")` will fail on Windows hosts without system IANA TZ data. |
| Python files concise (< ~150 lines), modular | Pass | `authorize.py` (35), `test_server.py` (58), `server.py` (68), `google_auth.py` (89), `main.py` (91), `gmail_tools.py` (114), `calendar_tools.py` (133). Clean separation of auth, Gmail, Calendar, and MCP layer. |

### B. Exact Toolset & Safety Boundaries
`server.py` exposes **exactly 6 `@mcp.tool()` tools**, matching the L06 specification:
1. `search_emails(query: str, max_results: int = 10) -> list[dict]`
2. `read_email(message_id: str) -> dict`
3. `create_draft(to: str, subject: str, body: str) -> dict`
4. `list_events(days_ahead: int = 7) -> list[dict]`
5. `find_free_slots(date: str, duration_minutes: int = 30) -> list[dict]`
6. `create_event(title: str, start: str, end: str, description: str = "") -> dict`

- **Descriptions:** All 6 have concise, accurate English docstrings (including range bounds and `Asia/Jerusalem` / draft-only notes).
- **No send or delete tools:** Verified. Zero extra tools exist. Google API calls are strictly limited to `messages.list`, `messages.get`, `drafts.create`, `events.list`, and `events.insert` (with `sendUpdates="none"`).

### C. Code-Level Edge Cases & Subtle Bugs
1. **Stale credential cache (`google_auth.py` lines 54–81):** `get_credentials()` and `_service()` use `@lru_cache`. If a user starts the server with a token missing `gmail.readonly` (e.g., an L05 token) and then runs `authorize.py` in another terminal, the running MCP server keeps the cached `Credentials` and continues failing until restarted. Also, if an access token expires and `refresh_token` is revoked mid-session, `googleapiclient`'s internal HTTP refresh can raise a raw `RefreshError` instead of `GoogleAuthError`.
2. **Missing `tzdata` (`pyproject.toml`, `uv.lock`):** On Windows, Python's `zoneinfo.ZoneInfo("Asia/Jerusalem")` requires `tzdata` in dependencies.
3. **Uncaught `HttpError` & input edge cases (`gmail_tools.py`, `calendar_tools.py`):**
   - Invalid `message_id` (404), malformed Gmail query, or invalid `date` (`"2026/11/25"`) raise raw `HttpError`/`ValueError` instead of friendly structured/actionable error messages.
   - `search_emails` performs `1 + N` sequential HTTP calls (up to 51 calls when `max_results=50`); batching would be cleaner.
   - `find_free_slots` silently clamps/returns `[]` for past dates and ignores declined events (`responseStatus == "declined"`), though it properly ignores `"transparent"` ("free") events and handles all-day events accurately.
   - `list_events` and `search_emails` silently clamp `days_ahead` (`1–90`) and `max_results` (`1–50`) instead of documenting/validating out-of-range inputs explicitly.
4. **Leftover L05 script (`main.py`):** Kept in repo root; documented in `README.md` and `PRD.md` as last week's test script. Not imported by `server.py`, though placing legacy L05 files in a subfolder or clearly noting why it remains avoids confusion.

### D. Testing, Registration & `reflection.md`
- **`test_server.py`:** Uses `mcp.ClientSession` + `stdio_client` to spawn `server.py`, assert the exact 6 tool names, and call `list_events(days_ahead=1)`. **Fails portability check** because line 15 hardcodes `PRIVATE_DIR` instead of reading `os.environ.get("GOOGLE_PRIVATE_DIR")`. Also lacks offline unit tests (e.g., `pytest` with mocks) for the remaining 5 tools and auth error paths.
- **MCP Registration:** `README.md` documents `claude mcp add gmail-calendar ...` (with personal path hardcoded). No generic JSON config example (e.g., for Antigravity `.agents/mcp_config.json` / Claude Desktop / `.mcp.json`) is provided.
- **`reflection.md` (43 lines):** Contains all 4 required headings verbatim and thoughtful, non-placeholder answers grounded in real runs (e.g., the `22:57 + 4h = 02:57` next-day edge case, deliberate send/delete boundary test, `Study group` calendar verification, L05 vs L06 comparison table, and accurate scope-vs-code analysis).
  - **Minor gap:** `reflection.md` stops at Prompt 15 (`6d8de25`), does not reflect Prompt 16 (the meeting coordinator end-to-end flow) or `test_server.py`, and still lists visually checking Gmail Drafts as an open manual check.

---

## 3. Beyond-Baseline Check: `README.md`, `PRD.md`, and 100/100 Readiness

### `README.md` Evaluation (235 lines)
- **Strengths:** Clear value proposition, clean 6-tool table, explicit `authorize.py` workflow, `mcp dev` inspector command, secrets warning, and complete chronological `Prompts Log` (Prompts 1–16).
- **Gaps:**
  1. Hardcoded personal macOS path and personal email address (see Section 1).
  2. **Out-of-date `Files` table (lines 81–88):** Omits `test_server.py`, `PRD.md`, and `reflection.md`.
  3. **Missing Test / Verification section:** Does not document `uv run test_server.py` (only mentions it in Prompt 12).
  4. **Missing cross-platform & JSON config examples:** Only shows `bash` `export` and `claude mcp add`; lacks PowerShell (`$env:GOOGLE_PRIVATE_DIR=...`) and a generic `mcpServers` JSON snippet (`.agents/mcp_config.json`).

### `PRD.md` Evaluation (116 lines)
- **Strengths:** Present, well-structured, and covers Purpose, Goals/Non-goals, ASCII Architecture diagram, SDK `<2` pin rationale, full 6-tool contract table, Security boundaries (including exact Google API method allowlist and the OAuth scope limitation), Environment variables, and Acceptance criteria.
- **Gaps for a 100/100 PRD:**
  1. **Factually inaccurate acceptance criterion (line 115):** States *"No file in the repository is 150 lines or longer"*—actually `README.md` (235 lines) and `uv.lock` exceed 150 lines; should specify *"No Python source file..."*.
  2. **Hardcoded personal path in Section 6 (line 105).**
  3. **Missing Error Handling & Failure Mode contract:** Section 6 claims tools return a clear error, but the PRD does not define error behavior for invalid dates/ranges, 404/403/429 Google API errors, stale cached credentials after re-authorization, or missing `tzdata`.
  4. **Missing Verification / Test Strategy section:** Does not link acceptance criteria to `test_server.py` and boundary test scenarios.
  5. **Minor edge cases undocumented:** Declined calendar events, long-running session re-auth requiring server restart, and Windows timezone dependency (`tzdata`).

---

## 4. Prioritized Action Plan to Reach 100 / 100

### P0 — Must Fix (Blocks Portability & Privacy)
1. **Fix `test_server.py` hardcoded path:** Read `GOOGLE_PRIVATE_DIR` from `os.environ.get("GOOGLE_PRIVATE_DIR")`; fail with a clear error message if unset rather than hardcoding `/Users/<user>/Desktop/roma-ai3`.
2. **Sanitize personal paths and email:** Replace `/Users/<user>/Desktop/roma-ai3` in `README.md` (usage sections) and `PRD.md` (Section 6) with placeholders like `/path/to/private-folder` and `/path/to/roma-ai3` (and keep secrets outside the repo directory). Redact `<personal-email>@gmail.com` and personal paths in the Prompts Log (or note they were redacted for privacy).
3. **Add `tzdata` to `pyproject.toml` and re-lock (`uv lock`):** Ensures `ZoneInfo("Asia/Jerusalem")` works on Windows as well as macOS/Linux.

### P1 — High Impact (Completeness & Professionalism)
4. **Update `README.md`:**
   - Add `PRD.md`, `reflection.md`, and `test_server.py` to the `Files` table.
   - Add a **Testing / Verification** section (`uv run test_server.py`).
   - Add PowerShell `GOOGLE_PRIVATE_DIR` instructions and a placeholder JSON snippet for Antigravity (`.agents/mcp_config.json`) / Claude Desktop.
5. **Tighten `PRD.md`:**
   - Fix line 115 (*"No Python file..."*).
   - Add an **Error Handling & Edge Cases** subsection and a **Verification Plan** section.
6. **Update `reflection.md`:** Add observations from Prompt 16 (meeting coordinator flow) and `test_server.py`, and confirm manual inspection of the created Gmail draft.

### P2 — Senior-Engineer Polish
7. **Handle credential reload & Google `HttpError` cleanly:** Clear `@lru_cache` or check `token.json` `st_mtime` in `google_auth.py`; wrap `googleapiclient.errors.HttpError` and date/time `ValueError` in concise, actionable messages.
8. **Add offline unit tests (`pytest`):** Test `find_free_slots`, `create_event` (`end <= start`), `gmail_tools` HTML stripping/truncation, and `google_auth` failure modes using mocks so tests run in CI or on any grader's machine without live Google credentials.
9. **Expand `.gitignore`:** Add `.pytest_cache/`, `.ruff_cache/`, `Thumbs.db`, `.vscode/`, `.idea/`, and local `.mcp.json` / `.agents/mcp_config.json` if needed.
