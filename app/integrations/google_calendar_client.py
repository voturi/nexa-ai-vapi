"""Google Calendar integration client."""
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import structlog
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.core.config import settings

logger = structlog.get_logger()

SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events",
]


class GoogleCalendarClient:
    """Client for Google Calendar API operations."""

    def __init__(self, credentials_data: dict):
        """
        Initialize with decrypted credential data.

        Args:
            credentials_data: Dict containing access_token, refresh_token, etc.
        """
        self.credentials_data = credentials_data
        self._credentials: Optional[Credentials] = None
        self._service = None

    def _build_credentials(self) -> Credentials:
        """Build Google OAuth credentials from stored data."""
        if self._credentials and self._credentials.valid:
            return self._credentials

        self._credentials = Credentials(
            token=self.credentials_data.get("access_token"),
            refresh_token=self.credentials_data.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_OAUTH_CLIENT_ID,
            client_secret=settings.GOOGLE_OAUTH_CLIENT_SECRET,
            scopes=SCOPES,
        )
        return self._credentials

    def _get_service(self):
        """Get or create the Calendar API service."""
        if self._service is None:
            creds = self._build_credentials()
            self._service = build("calendar", "v3", credentials=creds)
        return self._service

    @property
    def token_refreshed(self) -> bool:
        """Check if the token was refreshed during the last API call."""
        if self._credentials is None:
            return False
        return (
            self._credentials.token != self.credentials_data.get("access_token")
        )

    def get_refreshed_credentials(self) -> dict:
        """Return updated credential data if token was refreshed."""
        if not self.token_refreshed or self._credentials is None:
            return self.credentials_data

        updated = dict(self.credentials_data)
        updated["access_token"] = self._credentials.token
        if self._credentials.expiry:
            updated["token_expiry"] = self._credentials.expiry.isoformat()
        return updated

    async def list_calendars(self) -> List[Dict[str, Any]]:
        """List all calendars accessible to the user."""
        service = self._get_service()
        result = service.calendarList().list().execute()
        calendars = result.get("items", [])
        return [
            {
                "id": cal["id"],
                "summary": cal.get("summary", ""),
                "primary": cal.get("primary", False),
                "access_role": cal.get("accessRole", ""),
            }
            for cal in calendars
        ]

    async def check_availability(
        self,
        calendar_id: str,
        date: str,
        duration_minutes: int = 60,
        business_hours: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Check available time slots for a given date.

        Uses the FreeBusy API to find busy periods, then derives
        available slots from business hours minus busy times.

        Args:
            calendar_id: Google Calendar ID to check
            date: Date string in YYYY-MM-DD format
            duration_minutes: Required slot duration in minutes
            business_hours: Dict with 'start' and 'end' times (e.g. {"start": "09:00", "end": "17:00"})

        Returns:
            Dict with available_slots list and metadata
        """
        if business_hours is None:
            business_hours = {"start": "09:00", "end": "17:00"}

        try:
            target_date = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            return {"available_slots": [], "error": "Invalid date format"}

        # Build time range for the day
        day_start_str = f"{date}T{business_hours['start']}:00"
        day_end_str = f"{date}T{business_hours['end']}:00"

        # Parse into datetime for slot calculation
        day_start = datetime.strptime(day_start_str, "%Y-%m-%dT%H:%M:%S")
        day_end = datetime.strptime(day_end_str, "%Y-%m-%dT%H:%M:%S")

        service = self._get_service()

        # Query FreeBusy API
        body = {
            "timeMin": day_start_str + "Z",
            "timeMax": day_end_str + "Z",
            "items": [{"id": calendar_id}],
        }

        try:
            freebusy_result = service.freebusy().query(body=body).execute()
        except HttpError as e:
            logger.error("google_calendar_freebusy_error", error=str(e))
            return {"available_slots": [], "error": f"Calendar API error: {e}"}

        # Extract busy periods
        busy_periods = []
        calendar_data = freebusy_result.get("calendars", {}).get(calendar_id, {})
        for busy in calendar_data.get("busy", []):
            busy_start = datetime.fromisoformat(busy["start"].replace("Z", "+00:00")).replace(tzinfo=None)
            busy_end = datetime.fromisoformat(busy["end"].replace("Z", "+00:00")).replace(tzinfo=None)
            busy_periods.append((busy_start, busy_end))

        # Sort busy periods
        busy_periods.sort(key=lambda x: x[0])

        # Generate available slots from gaps
        available_slots = []
        slot_duration = timedelta(minutes=duration_minutes)
        current = day_start

        for busy_start, busy_end in busy_periods:
            # Generate slots in the gap before this busy period
            while current + slot_duration <= busy_start:
                available_slots.append({
                    "datetime": current.strftime("%Y-%m-%dT%H:%M:%S"),
                    "slot": current.strftime("%I:%M %p").lstrip("0"),
                    "available": True,
                })
                current += slot_duration
            # Skip past the busy period
            if busy_end > current:
                current = busy_end

        # Generate slots after the last busy period
        while current + slot_duration <= day_end:
            available_slots.append({
                "datetime": current.strftime("%Y-%m-%dT%H:%M:%S"),
                "slot": current.strftime("%I:%M %p").lstrip("0"),
                "available": True,
            })
            current += slot_duration

        date_formatted = target_date.strftime("%A, %B %d, %Y")

        return {
            "available_slots": available_slots,
            "date": date,
            "date_formatted": date_formatted,
            "duration_minutes": duration_minutes,
            "total_slots": len(available_slots),
        }

    async def create_event(
        self,
        calendar_id: str,
        summary: str,
        start_datetime: str,
        duration_minutes: int = 60,
        description: Optional[str] = None,
        location: Optional[str] = None,
        attendee_email: Optional[str] = None,
        timezone: str = "Australia/Sydney",
    ) -> Dict[str, Any]:
        """
        Create a calendar event.

        Args:
            calendar_id: Google Calendar ID
            summary: Event title
            start_datetime: ISO format datetime string
            duration_minutes: Event duration in minutes
            description: Optional event description
            location: Optional event location
            attendee_email: Optional attendee email to invite
            timezone: Timezone for the event

        Returns:
            Dict with event_id, html_link, and status
        """
        start = datetime.fromisoformat(start_datetime.replace("Z", "+00:00")).replace(tzinfo=None)
        end = start + timedelta(minutes=duration_minutes)

        event = {
            "summary": summary,
            "start": {
                "dateTime": start.strftime("%Y-%m-%dT%H:%M:%S"),
                "timeZone": timezone,
            },
            "end": {
                "dateTime": end.strftime("%Y-%m-%dT%H:%M:%S"),
                "timeZone": timezone,
            },
        }

        if description:
            event["description"] = description
        if location:
            event["location"] = location
        if attendee_email:
            event["attendees"] = [{"email": attendee_email}]

        service = self._get_service()

        try:
            created = service.events().insert(
                calendarId=calendar_id,
                body=event,
                sendUpdates="all" if attendee_email else "none",
            ).execute()

            logger.info(
                "google_calendar_event_created",
                event_id=created["id"],
                calendar_id=calendar_id,
            )

            return {
                "event_id": created["id"],
                "html_link": created.get("htmlLink", ""),
                "status": created.get("status", "confirmed"),
                "start": created["start"],
                "end": created["end"],
            }

        except HttpError as e:
            logger.error("google_calendar_create_event_error", error=str(e))
            raise

    async def cancel_event(
        self,
        calendar_id: str,
        event_id: str,
    ) -> bool:
        """Cancel (delete) a calendar event."""
        service = self._get_service()

        try:
            service.events().delete(
                calendarId=calendar_id,
                eventId=event_id,
                sendUpdates="all",
            ).execute()
            logger.info("google_calendar_event_cancelled", event_id=event_id)
            return True
        except HttpError as e:
            logger.error("google_calendar_cancel_event_error", event_id=event_id, error=str(e))
            return False
