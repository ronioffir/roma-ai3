# Reflection: L06, the gmail-calendar MCP server

## What did we ask the agent?

We asked Claude Code to build an MCP server named `gmail-calendar` (Python, FastMCP, uv, stdio) with exactly six tools: `search_emails`, `read_email`, `create_draft`, `list_events`, `find_free_slots` and `create_event`. It had to reuse last week's Google client file and `token.json` through the `GOOGLE_PRIVATE_DIR` environment variable, without copying or printing them and without opening a browser.

Then we registered the server in Claude Code and used it in plain language:

- "What do I have in my calendar tomorrow?"
- "Write a Gmail draft to myself with the subject 'L06 test' and add a calendar event 4 hours from now called 'MCP works'."
- "Send the 'L06 test' draft and delete the 'Study group' event." This one was a deliberate test of the limits.

Around the work we also asked for a `.gitignore`, a `PRD.md`, a `README.md` with a Prompts Log, and a commit and push after every prompt.

## How did we check that the result is correct?

- **Against the real account.** The calendar answer matched the one event actually in the calendar ("Test event from Python", 23:16 to 00:16). After the create request, `list_events` showed "MCP works" at 02:57 to 03:57 on Nov 25, and the draft tool returned a draft id with the status "It was NOT sent".
- **By reading the details, not just the "done".** The agent pointed out that "today, 4 hours from now" was no longer today (22:57 + 4h = 02:57 the next day), and that it had chosen the one-hour length and the draft body itself. Those are the places a result can be quietly wrong.
- **By testing the boundary.** When asked to send and delete, the agent did neither and said so. It also checked 90 days ahead and reported that no "Study group" event exists.
- **In git.** Before every commit we looked at the staged file list. Only `README.md` (and now `reflection.md`) was staged; `token.json` and `client_secret*.json` never were.

What is still worth doing by hand: open Gmail Drafts and Google Calendar and look at the draft and the event with our own eyes.

## Which tool did we leave out, and why?

We left out every tool that sends or deletes: no `send_email`, no `delete_email`, no `delete_event`. There is also no tool that edits an existing event.

The reason is that these actions cannot be undone and they reach other people. A sent email cannot be pulled back, and a deleted event is gone. An agent can misread a request or pick the wrong recipient or the wrong event, so the server only does things that are easy to review and reverse: a draft waits for a human to press Send, and a new event can be removed by hand.

The limit is in the server's code, not in a promise from the agent: the tool does not exist, so no prompt can make the agent send or delete through this server. The token is not the limit. Its `gmail.compose` scope would allow sending a draft and its `calendar.events` scope would allow deleting an event, so the code is the only thing standing in the way, and it must stay that way. The cost is small: we send drafts and delete events ourselves, as we saw when the "MCP works" event landed on the wrong date and had to be moved by hand.

## L05 vs L06: what changed?

| | L05 | L06 |
|---|---|---|
| What we built | A Python script (`main.py`) that calls the Google APIs directly | An MCP server that exposes those calls as six tools |
| Who decides what happens | We do, in code: the script always creates the same test draft and test event | The agent does, per request: it picks the tools and fills in the arguments |
| How we use it | `uv run main.py` in a terminal | A sentence in Claude Code |
| To do something new | Edit the code and run it again | Ask a different question |
| Where safety comes from | We read the few lines the script runs | The tool list and token permissions set the limits; we check what the agent did |

The Google side did not change: the same client file, the same `token.json`, the same APIs. What changed is the layer on top. In L05 the program was the user of the API. In L06 the agent is, which makes it far more flexible and is also why we had to think about which tools not to give it.
