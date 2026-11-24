"""One-time Google sign-in for the gmail-calendar MCP server.

Run by hand in a terminal (NOT by the server):

    GOOGLE_PRIVATE_DIR=/path/to/private/folder uv run authorize.py

It opens the browser for Google sign-in and saves token.json inside
GOOGLE_PRIVATE_DIR, replacing the old token in place. The MCP server itself
never opens a browser; it only reads the token this script saves.
"""

import sys

from google_auth_oauthlib.flow import InstalledAppFlow

from google_auth import SCOPES, GoogleAuthError, client_file, token_file


def main() -> None:
    try:
        client, token = client_file(), token_file()
    except GoogleAuthError as exc:
        sys.exit(str(exc))
    flow = InstalledAppFlow.from_client_secrets_file(str(client), SCOPES)
    creds = flow.run_local_server(port=0, authorization_prompt_message="Opening the browser for Google sign-in...")
    missing = [scope for scope in SCOPES if scope not in (creds.scopes or [])]
    if missing:
        sys.exit("Sign-in finished but some permissions were not approved. Nothing was saved.")
    token.write_text(creds.to_json())
    token.chmod(0o600)
    print("Signed in. token.json was saved in GOOGLE_PRIVATE_DIR.")


if __name__ == "__main__":
    main()
