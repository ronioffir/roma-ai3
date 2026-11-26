"""Google Calendar operations: list events, find free slots, create an event.

Nothing here deletes or changes existing events, and no invitations are sent.
All times are in the Asia/Jerusalem time zone.
"""

from datetime import date as date_type
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from google_auth import CALENDAR_EVENTS, TIME_ZONE, calendar, execute, require_scope

TZ = ZoneInfo(TIME_ZONE)
DAY_START = time(8, 0)  # free slots are searched between 08:00 ...
DAY_END = time(20, 0)  # ... and 20:00


def _parse(value: str) -> datetime:
    """Parse an ISO 8601 date-time; a value without an offset is Asia/Jerusalem."""
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValueError(f"'{value}' is not a valid date-time. Use ISO 8601, e.g. 2026-12-01T14:00.") from None
    return parsed.replace(tzinfo=TZ) if parsed.tzinfo is None else parsed.astimezone(TZ)


def _parse_day(value: str) -> date_type:
    try:
        return date_type.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValueError(f"'{value}' is not a valid date. Use YYYY-MM-DD, e.g. 2026-12-01.") from None


def _blocks_time(event: dict) -> bool:
    """False for events marked "free" and for invitations the user declined."""
    if event.get("transparency") == "transparent":
        return False
    return not any(a.get("self") and a.get("responseStatus") == "declined" for a in event.get("attendees", []))


def _event_times(event: dict) -> tuple[datetime, datetime]:
    """Start and end of an event; all-day events run from midnight to midnight."""
    times = []
    for key in ("start", "end"):
        raw = event[key]
        if "dateTime" in raw:
            times.append(_parse(raw["dateTime"]))
        else:
            times.append(datetime.combine(date_type.fromisoformat(raw["date"]), time(0), TZ))
    return times[0], times[1]


def _fetch(start: datetime, end: datetime) -> list[dict]:
    require_scope(CALENDAR_EVENTS)
    events, page_token = [], None
    while True:
        request = calendar().events().list(
            calendarId="primary",
            timeMin=start.isoformat(),
            timeMax=end.isoformat(),
            singleEvents=True,
            orderBy="startTime",
            timeZone=TIME_ZONE,
            pageToken=page_token,
        )
        page = execute(request, "read the calendar")
        events.extend(page.get("items", []))
        page_token = page.get("nextPageToken")
        if not page_token:
            return events


def list_events(days_ahead: int = 7) -> list[dict]:
    days = max(1, min(int(days_ahead), 90))
    now = datetime.now(TZ)
    results = []
    for event in _fetch(now, now + timedelta(days=days)):
        start, end = _event_times(event)
        results.append(
            {
                "event_id": event["id"],
                "title": event.get("summary", "(no title)"),
                "start": start.isoformat(),
                "end": end.isoformat(),
                "all_day": "date" in event["start"],
                "location": event.get("location", ""),
                "link": event.get("htmlLink", ""),
            }
        )
    return results


def find_free_slots(date: str, duration_minutes: int = 30) -> list[dict]:
    day = _parse_day(date)
    minutes = int(duration_minutes)
    if minutes <= 0:
        raise ValueError("duration_minutes must be greater than 0.")
    window_start = datetime.combine(day, DAY_START, TZ)
    window_end = datetime.combine(day, DAY_END, TZ)
    # Do not offer times that have already passed today.
    now = datetime.now(TZ).replace(second=0, microsecond=0) + timedelta(minutes=1)
    cursor = max(window_start, now)

    busy = [_event_times(event) for event in _fetch(window_start, window_end) if _blocks_time(event)]

    slots = []
    for start, end in sorted(busy):
        if start > cursor:
            slots.append((cursor, min(start, window_end)))
        cursor = max(cursor, end)
    if cursor < window_end:
        slots.append((cursor, window_end))
    return [
        {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "minutes": int((end - start).total_seconds() // 60),
        }
        for start, end in slots
        if end - start >= timedelta(minutes=minutes)
    ]


def create_event(title: str, start: str, end: str, description: str = "") -> dict:
    require_scope(CALENDAR_EVENTS)
    start_at, end_at = _parse(start), _parse(end)
    if end_at <= start_at:
        raise ValueError("The event end must be after its start.")
    body = {
        "summary": title,
        "description": description,
        "start": {"dateTime": start_at.isoformat(), "timeZone": TIME_ZONE},
        "end": {"dateTime": end_at.isoformat(), "timeZone": TIME_ZONE},
    }
    request = calendar().events().insert(calendarId="primary", body=body, sendUpdates="none")
    event = execute(request, "create the event")
    return {
        "event_id": event["id"],
        "title": event.get("summary", title),
        "start": start_at.isoformat(),
        "end": end_at.isoformat(),
        "link": event.get("htmlLink", ""),
    }
