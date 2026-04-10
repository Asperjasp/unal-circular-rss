"""
Google Calendar Integration Service
=====================================
Integrates with Google Calendar API v3 for syncing events.

Setup:
1. Go to Google Cloud Console → APIs & Services → Enable Google Calendar API
2. Create OAuth 2.0 credentials (Desktop App or Web App)
3. Download the client_secret.json file
4. On first run, it will open a browser for OAuth consent
5. After consent, tokens are stored locally for future use

Alternative (Service Account - recommended for server):
1. Create a Service Account in Google Cloud Console
2. Download the JSON key file
3. Share your calendar with the service account email
4. Set GOOGLE_SERVICE_ACCOUNT_FILE in .env
"""

import logging
import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

# Google Calendar API v3 base
CALENDAR_API_BASE = "https://www.googleapis.com/calendar/v3"


class GoogleCalendarService:
    """
    Service for Google Calendar integration.

    Supports two auth modes:
    1. OAuth2 (interactive) - for desktop/development
    2. Service Account (non-interactive) - for server/production
    """

    def __init__(
        self,
        credentials_file: Optional[str] = None,
        service_account_file: Optional[str] = None,
        token_file: str = "google_token.json",
    ):
        self.credentials_file = credentials_file
        self.service_account_file = service_account_file
        self.token_file = token_file
        self._service = None
        self._credentials = None

    def _get_service(self):
        """Get or create the Google Calendar service object"""
        if self._service:
            return self._service

        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build
        except ImportError:
            raise ImportError(
                "Google API libraries not installed. Run: "
                "pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib"
            )

        if self.service_account_file and Path(self.service_account_file).exists():
            # Service Account auth (recommended for production)
            credentials = service_account.Credentials.from_service_account_file(
                self.service_account_file,
                scopes=["https://www.googleapis.com/auth/calendar"],
            )
            self._service = build("calendar", "v3", credentials=credentials)
            logger.info("Google Calendar: Authenticated via Service Account")

        elif self.credentials_file and Path(self.credentials_file).exists():
            # OAuth2 auth (for development)
            from google.auth.transport.requests import Request
            from google_auth_oauthlib.flow import InstalledAppFlow

            creds = None
            token_path = Path(self.token_file)

            if token_path.exists():
                from google.oauth2.credentials import Credentials
                creds = Credentials.from_authorized_user_file(
                    str(token_path),
                    ["https://www.googleapis.com/auth/calendar"],
                )

            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_file,
                        ["https://www.googleapis.com/auth/calendar"],
                    )
                    creds = flow.run_local_server(port=0)

                # Save tokens for next run
                with open(str(token_path), "w") as token:
                    token.write(creds.to_json())

            self._service = build("calendar", "v3", credentials=creds)
            logger.info("Google Calendar: Authenticated via OAuth2")

        else:
            raise ValueError(
                "No Google credentials configured. Set GOOGLE_SERVICE_ACCOUNT_FILE "
                "or GOOGLE_CREDENTIALS_FILE in .env"
            )

        return self._service

    # ── Calendar Management ───────────────────────────────────────────

    async def list_calendars(self) -> List[Dict[str, Any]]:
        """List all calendars the user has access to"""
        import asyncio

        service = self._get_service()
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: service.calendarList().list().execute(),
        )
        return [
            {
                "id": cal["id"],
                "summary": cal.get("summary", ""),
                "primary": cal.get("primary", False),
                "timeZone": cal.get("timeZone", ""),
            }
            for cal in result.get("items", [])
        ]

    # ── Events ────────────────────────────────────────────────────────

    async def create_event(
        self,
        summary: str,
        start_datetime: str,
        end_datetime: str,
        description: Optional[str] = None,
        location: Optional[str] = None,
        attendees: Optional[List[str]] = None,
        calendar_id: str = "primary",
        timezone: str = "America/Bogota",
        send_notifications: bool = True,
    ) -> Dict[str, Any]:
        """
        Create a calendar event.

        Args:
            summary: Event title
            start_datetime: ISO format datetime (e.g., "2026-03-15T10:00:00")
            end_datetime: ISO format datetime
            description: Event description
            location: Event location
            attendees: List of email addresses
            calendar_id: Calendar to add event to (default: primary)
            timezone: Timezone (default: America/Bogota)
        """
        import asyncio

        event = {
            "summary": summary,
            "start": {
                "dateTime": start_datetime,
                "timeZone": timezone,
            },
            "end": {
                "dateTime": end_datetime,
                "timeZone": timezone,
            },
        }

        if description:
            event["description"] = description
        if location:
            event["location"] = location
        if attendees:
            event["attendees"] = [{"email": email} for email in attendees]

        service = self._get_service()
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: service.events()
            .insert(
                calendarId=calendar_id,
                body=event,
                sendNotifications=send_notifications,
            )
            .execute(),
        )

        logger.info(f"Created Google Calendar event: {summary} ({result.get('id')})")
        return {
            "id": result.get("id"),
            "summary": result.get("summary"),
            "htmlLink": result.get("htmlLink"),
            "start": result.get("start"),
            "end": result.get("end"),
            "status": result.get("status"),
        }

    async def create_meeting_event(
        self,
        company_name: str,
        meeting_type: str = "Reunión comercial",
        start_datetime: str = "",
        duration_minutes: int = 60,
        attendees: Optional[List[str]] = None,
        notes: Optional[str] = None,
        calendar_id: str = "primary",
    ) -> Dict[str, Any]:
        """
        Convenience method to create a meeting event for a company.
        Auto-generates title and description.
        """
        if not start_datetime:
            # Default to tomorrow at 10:00 AM
            tomorrow = datetime.now() + timedelta(days=1)
            start_datetime = tomorrow.replace(hour=10, minute=0, second=0).isoformat()

        # Calculate end time
        start = datetime.fromisoformat(start_datetime)
        end = start + timedelta(minutes=duration_minutes)

        summary = f"{meeting_type} - {company_name}"
        description = f"**Empresa:** {company_name}\n**Tipo:** {meeting_type}\n"
        if notes:
            description += f"\n**Notas:**\n{notes}"

        return await self.create_event(
            summary=summary,
            start_datetime=start.isoformat(),
            end_datetime=end.isoformat(),
            description=description,
            attendees=attendees,
            calendar_id=calendar_id,
        )

    async def get_upcoming_events(
        self, calendar_id: str = "primary", max_results: int = 20
    ) -> List[Dict[str, Any]]:
        """Get upcoming events from calendar"""
        import asyncio

        service = self._get_service()
        now = datetime.utcnow().isoformat() + "Z"

        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: service.events()
            .list(
                calendarId=calendar_id,
                timeMin=now,
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute(),
        )

        return [
            {
                "id": ev.get("id"),
                "summary": ev.get("summary", "Sin título"),
                "start": ev.get("start", {}).get("dateTime", ev.get("start", {}).get("date")),
                "end": ev.get("end", {}).get("dateTime", ev.get("end", {}).get("date")),
                "location": ev.get("location"),
                "htmlLink": ev.get("htmlLink"),
                "attendees": [a.get("email") for a in ev.get("attendees", [])],
            }
            for ev in result.get("items", [])
        ]

    async def delete_event(self, event_id: str, calendar_id: str = "primary") -> bool:
        """Delete a calendar event"""
        import asyncio

        service = self._get_service()
        try:
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: service.events().delete(calendarId=calendar_id, eventId=event_id).execute(),
            )
            return True
        except Exception as e:
            logger.error(f"Failed to delete event {event_id}: {e}")
            return False
