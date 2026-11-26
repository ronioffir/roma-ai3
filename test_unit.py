"""Offline unit tests: no network, no Google account, no secret files needed.

Run with:  uv run python -m unittest -v test_unit.py
"""

import asyncio
import base64
import os
import tempfile
import unittest
from datetime import timedelta
from unittest import mock

import calendar_tools
import gmail_tools
import google_auth
import server

EXPECTED_TOOLS = {"search_emails", "read_email", "create_draft", "list_events", "find_free_slots", "create_event"}
FORBIDDEN_WORDS = ("send", "delete", "trash", "remove", "update", "edit")


def _b64(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode()).decode()


def _event(start: str, end: str, **extra) -> dict:
    return {"start": {"dateTime": f"2030-01-08T{start}:00+02:00"}, "end": {"dateTime": f"2030-01-08T{end}:00+02:00"}, **extra}


class ServerTools(unittest.TestCase):
    def test_exactly_six_tools_and_none_sends_or_deletes(self):
        names = {tool.name for tool in asyncio.run(server.mcp.list_tools())}
        self.assertEqual(names, EXPECTED_TOOLS)
        for name in names:
            self.assertFalse(any(word in name for word in FORBIDDEN_WORDS), name)


class GoogleAuth(unittest.TestCase):
    def setUp(self):
        google_auth.reset_cache()

    def test_private_dir_not_set(self):
        with mock.patch.dict(os.environ, clear=True):
            with self.assertRaises(google_auth.GoogleAuthError):
                google_auth.get_credentials()

    def test_private_dir_does_not_exist(self):
        with mock.patch.dict(os.environ, {"GOOGLE_PRIVATE_DIR": "/no/such/folder/for-this-test"}):
            with self.assertRaises(google_auth.GoogleAuthError):
                google_auth.get_credentials()

    def test_token_file_missing(self):
        with tempfile.TemporaryDirectory() as folder, mock.patch.dict(os.environ, {"GOOGLE_PRIVATE_DIR": folder}):
            with self.assertRaises(google_auth.GoogleAuthError) as caught:
                google_auth.get_credentials()
        self.assertIn("authorize.py", str(caught.exception))

    def test_token_is_reloaded_when_the_file_changes(self):
        with tempfile.TemporaryDirectory() as folder, mock.patch.dict(os.environ, {"GOOGLE_PRIVATE_DIR": folder}):
            token = os.path.join(folder, "token.json")
            open(token, "w").close()
            loader = mock.Mock(side_effect=lambda path: mock.Mock(valid=True))
            with mock.patch.object(google_auth.Credentials, "from_authorized_user_file", loader):
                first = google_auth.get_credentials()
                self.assertIs(google_auth.get_credentials(), first)  # unchanged file: cached
                os.utime(token, ns=(1, 1))  # as if authorize.py had rewritten the file
                self.assertIsNot(google_auth.get_credentials(), first)
        self.assertEqual(loader.call_count, 2)


class GmailTools(unittest.TestCase):
    def test_strip_html_drops_scripts_and_tags(self):
        text = gmail_tools._strip_html("<script>alert('x')</script><style>p{}</style><p>Hello <b>there</b> &amp; hi</p>")
        self.assertNotIn("alert", text)
        self.assertNotIn("<", text)
        self.assertIn("Hello", text)
        self.assertIn("& hi", text)

    def test_plain_text_is_preferred_over_html(self):
        payload = {
            "parts": [
                {"mimeType": "text/html", "body": {"data": _b64("<p>HTML version</p>")}},
                {"mimeType": "text/plain", "body": {"data": _b64("Plain version")}},
            ]
        }
        self.assertEqual(gmail_tools._body_text(payload), "Plain version")

    def test_long_body_is_truncated(self):
        long_text = "a" * (gmail_tools.MAX_BODY_CHARS + 5)
        message = {"id": "m1", "payload": {"mimeType": "text/plain", "body": {"data": _b64(long_text)}, "headers": []}}
        client = mock.MagicMock()
        client.users().messages().get().execute.return_value = message
        with mock.patch.object(gmail_tools, "gmail", return_value=client), mock.patch.object(gmail_tools, "require_scope"):
            result = gmail_tools.read_email("m1")
        self.assertTrue(result["body_truncated"])
        self.assertEqual(len(result["body"]), gmail_tools.MAX_BODY_CHARS)


class CalendarTools(unittest.TestCase):
    def test_free_slots_skip_free_and_declined_events(self):
        events = [
            _event("09:00", "10:00", transparency="transparent"),
            _event("11:00", "12:00", attendees=[{"self": True, "responseStatus": "declined"}]),
            _event("13:00", "14:00", attendees=[{"self": True, "responseStatus": "accepted"}]),
        ]
        with mock.patch.object(calendar_tools, "_fetch", return_value=events):
            slots = calendar_tools.find_free_slots("2030-01-08", 60)
        self.assertEqual([(s["start"][11:16], s["end"][11:16]) for s in slots], [("08:00", "13:00"), ("14:00", "20:00")])

    def test_bad_date_gets_format_guidance(self):
        with self.assertRaisesRegex(ValueError, "YYYY-MM-DD"):
            calendar_tools.find_free_slots("01/12/2026", 30)

    def test_create_event_rejects_bad_times(self):
        with mock.patch.object(calendar_tools, "require_scope"), mock.patch.object(calendar_tools, "calendar") as client:
            with self.assertRaisesRegex(ValueError, "after its start"):
                calendar_tools.create_event("x", "2026-12-01T14:00", "2026-12-01T14:00")
            with self.assertRaisesRegex(ValueError, "ISO 8601"):
                calendar_tools.create_event("x", "tomorrow at ten", "2026-12-01T14:00")
            client.assert_not_called()  # nothing reached Google

    def test_naive_times_are_asia_jerusalem(self):
        parsed = calendar_tools._parse("2026-12-01T14:00")
        self.assertEqual(str(parsed.tzinfo), "Asia/Jerusalem")
        self.assertEqual(parsed.utcoffset(), timedelta(hours=2))
        self.assertEqual(calendar_tools._parse("2026-07-01T14:00").utcoffset(), timedelta(hours=3))  # summer time


if __name__ == "__main__":
    unittest.main()
