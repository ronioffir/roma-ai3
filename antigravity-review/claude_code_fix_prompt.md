# Claude Code Execution Prompt: Upgrade `roma-ai3` to 100/100 for Rami (L06)

Read `antigravity-review/review_report.md` for the full audit context, then apply all fixes below cleanly and methodically to bring the `gmail-calendar` MCP server (`roma-ai3`) from 90/100 to a 100/100 submission for Rami's L06 assignment ("MCP Server for Gmail and Calendar", Dr. Yoram Segal slides 21–37).

---

## 1. Non-Negotiable Constraints (Preserve Existing Strengths)

- **Exact 6 tools only:** `search_emails`, `read_email`, `create_draft`, `list_events`, `find_free_slots`, `create_event`.
- **Zero send or delete capability:** Never add `send_email`, `delete_email`, `delete_event`, event-editing tools, or invitation sending (`sendUpdates="none"` must remain).
- **MCP stack & transport:** Keep Python `>=3.12`, `FastMCP` (`mcp[cli]<2`), `uv`, and `stdio` transport.
- **Zero `stdout` pollution:** Never add `print()` or `stdout` logging inside `server.py`, `gmail_tools.py`, `calendar_tools.py`, or `google_auth.py`.
- **Time zone:** Enforce `Asia/Jerusalem` for all calendar inputs and outputs.
- **File size discipline:** Every `.py` file in the repository MUST stay **strictly under 150 lines** after all edits.
- **Strict Secret & Privacy Rules:**
  - Never print, read, copy, stage, or commit `token.json`, `client_secret*.json`, `credentials.json`, `.env`, or any personal local paths or personal email addresses.
  - Ensure `GOOGLE_PRIVATE_DIR` is always documented as pointing to a separate directory **outside** the Git repository (never inside `roma-ai3`).

---

## 2. Prioritized Implementation Checklist

### P0 — Critical Portability, Privacy & Cross-Platform Fixes

1. **Fix hardcoded path in `test_server.py` (lines 15 & 30):**
   - Remove the hardcoded personal macOS `PRIVATE_DIR` path.
   - Read `GOOGLE_PRIVATE_DIR` from `os.environ.get("GOOGLE_PRIVATE_DIR")`.
   - If `GOOGLE_PRIVATE_DIR` is unset, empty, or not an existing directory (`Path(private_dir).expanduser().is_dir()`), print a clear error message to `stderr` (or `stdout` in the test script) and exit non-zero (`return 1`), rather than overwriting the caller's environment variable.
   - Pass the validated `GOOGLE_PRIVATE_DIR` through to `StdioServerParameters(env={**os.environ, ...})`.

2. **Sanitize personal paths and email leaks in `README.md` and `PRD.md`:**
   - Replace every occurrence of the personal macOS path in `README.md` (setup instructions, `claude mcp add`, and the `Prompts Log`) and `PRD.md` (Section 6) with clean generic placeholders such as `/path/to/private-folder` (for `GOOGLE_PRIVATE_DIR`) and `/path/to/roma-ai3` (for `--directory`).
   - Replace the personal Gmail address in `README.md` (`Prompts Log`, Prompt 5) with `<your-email>@gmail.com` and replace the personal git username if needed with `<your-github-username>`.
   - Ensure `README.md` and `PRD.md` explicitly instruct keeping `GOOGLE_PRIVATE_DIR` **outside** the `roma-ai3` Git repository (e.g., `~/private/gmail-calendar` or `C:\Users\<user>\private\gmail-calendar`).

3. **Add `tzdata` for cross-platform Windows support (`pyproject.toml` & `uv.lock`):**
   - Add `"tzdata>=2024.1"` to `dependencies` in `pyproject.toml` so `ZoneInfo("Asia/Jerusalem")` works reliably on Windows as well as macOS and Linux.
   - Run `uv lock` to update `uv.lock` (if `uv` is installed in the current environment; if not, note clearly in your final summary that `uv lock` must be run).

---

### P1 — Documentation & Reflection Completeness

4. **Update `README.md`:**
   - Update the **Files** table to include `test_server.py`, `PRD.md`, and `reflection.md` (and keep `main.py` clearly labeled as the L05 legacy test script).
   - Add a **Testing / Verification** section showing how to run both the offline unit tests and the live MCP smoke test (`uv run test_server.py`) with `GOOGLE_PRIVATE_DIR` set.
   - Add **Windows PowerShell** instructions (`$env:GOOGLE_PRIVATE_DIR="C:\path\to\private-folder"`) alongside the existing macOS/Linux `bash` (`export GOOGLE_PRIVATE_DIR=/path/to/private-folder`) commands.
   - Add a sanitized JSON MCP client configuration snippet (suitable for Antigravity `.agents/mcp_config.json`, `.mcp.json`, or Claude Desktop) using placeholder paths only:
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

5. **Update `PRD.md`:**
   - Fix Section 7 (line 115) so the line-limit acceptance criterion accurately states: `"No Python file in the repository is 150 lines or longer."`
   - Add an **Error Handling & Edge Cases** subsection documenting:
     - Validation of `date` (`YYYY-MM-DD`), ISO 8601 `start`/`end`, `end > start`, `duration_minutes > 0`, and `max_results`/`days_ahead` bounds.
     - Actionable error behavior when `GOOGLE_PRIVATE_DIR` is missing/invalid, `token.json` is missing or lacks required scopes, or Google API calls return `HttpError` (401/403/404/429).
     - Calendar slot edge cases: `"transparent"` ("free") events ignored, declined attendee events ignored, all-day `"busy"` events blocking the day, past times on today's date excluded, and `Asia/Jerusalem` TZ enforcement (including `tzdata` on Windows).
   - Add a **Verification Plan** section linking the acceptance criteria to the offline unit tests and `test_server.py` (plus the manual send/delete boundary check).

6. **Update `reflection.md`:**
   - Keep all four required section headings verbatim (`What did we ask the agent?`, `How did we check that the result is correct?`, `Which tool did we leave out, and why?`, `L05 vs L06: what changed?`).
   - Append concise observations covering **Prompt 16** (the meeting coordinator end-to-end workflow) and **`test_server.py`** (automated stdio `tools/list` + `list_events` verification).
   - Update the note about checking Gmail Drafts by hand to mark the manual Gmail Draft verification as completed.

---

### P2 — Senior-Engineer Polish

7. **Improve credential reload & auth error handling in `google_auth.py`:**
   - Avoid stale cached credentials when a user re-runs `authorize.py` while the MCP server is still running (for example, key the credential/service cache on `(str(token_path), token_path.stat().st_mtime_ns)` or clear the caches if `token.json` mtime changed or an auth/refresh error occurs).
   - Ensure refresh errors (`google.auth.exceptions.RefreshError` or equivalent) raise `GoogleAuthError` with `REAUTH_HINT` without ever printing token contents or file paths containing secrets.
   - Keep `google_auth.py` strictly under 150 lines.

8. **Harden error handling & edge cases in `gmail_tools.py` and `calendar_tools.py`:**
   - Catch `googleapiclient.errors.HttpError` in Gmail and Calendar API calls and raise a clear, concise `RuntimeError` (without leaking raw stack traces or credentials) describing what failed (e.g., invalid query, message not found, Google API permission/quota error).
   - Catch invalid `date` / ISO 8601 `datetime` `ValueError`s in `calendar_tools.py` and re-raise with clear format guidance (`YYYY-MM-DD` for `date`, ISO 8601 such as `2026-12-01T14:00` for `start`/`end`).
   - In `find_free_slots`, also skip events where the current user's attendee entry (`attendee.get("self")`) has `responseStatus == "declined"`.
   - Keep both `gmail_tools.py` and `calendar_tools.py` strictly under 150 lines (extract small helpers if needed, do not duplicate error-handling boilerplate).

9. **Add lightweight offline unit tests (`test_unit.py`):**
   - Use Python's built-in `unittest` + `unittest.mock` (so tests run immediately via `uv run python -m unittest test_unit.py` or `pytest` without requiring extra dev dependencies) and keep `test_unit.py` under 150 lines.
   - Cover at minimum:
     - `server.py` exposes the exact 6 tool names and zero send/delete tools.
     - `google_auth.py` raises `GoogleAuthError` when `GOOGLE_PRIVATE_DIR` is unset, points to a non-existent folder, or lacks `token.json`.
     - `gmail_tools.py` strips HTML/scripts safely, prefers `text/plain`, and sets `body_truncated=True` over `MAX_BODY_CHARS`.
     - `calendar_tools.py` `find_free_slots` skips `"transparent"` and `"declined"` events, `create_event` rejects `end <= start` and malformed dates, and `Asia/Jerusalem` timezone is attached to naive datetimes.

10. **Expand `.gitignore`:**
    - Add `.pytest_cache/`, `.ruff_cache/`, `*.egg-info/`, `dist/`, `build/`, `Thumbs.db`, `.vscode/`, `.idea/`, `.mcp.json`, and `.agents/mcp_config.json`.

---

## 3. Verification & Git Workflow

1. **Line-count check:** Verify every `.py` file in the repository has `< 150` lines.
2. **Test execution:**
   - Run the offline unit tests: `uv run python -m unittest -v test_unit.py`.
   - Test `test_server.py` failure behavior when `GOOGLE_PRIVATE_DIR` is unset (confirms clean error exit instead of hardcoded path).
   - If `GOOGLE_PRIVATE_DIR` is configured in the local environment, run `uv run test_server.py` and confirm `PASS` with all 6 tools and `list_events(days_ahead=1)`.
3. **Secret & privacy scan:**
   - Run `git status` and `git diff` and verify zero secrets (`token.json`, `client_secret*.json`, `credentials.json`, `.env`) and zero personal local paths or personal emails exist anywhere in tracked or staged files.
4. **Commit & push:**
   - Stage only the intended modified/new non-secret files, commit with a clear message, and push to `origin main`.
   - Report the exact test outputs, line counts for all `.py` files, `git status`, commit hash, and `git push` result.
