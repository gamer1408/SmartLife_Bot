"""
Google Calendar Service
Handles OAuth flow and calendar operations
"""

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from datetime import datetime, timedelta
import json
import os
from typing import Optional, List, Dict
import logging

logger = logging.getLogger(__name__)


class CalendarService:
    """Google Calendar API integration service"""

    SCOPES = ['https://www.googleapis.com/auth/calendar']
    REDIRECT_URI = 'http://localhost:8080/callback'

    def __init__(self, db_manager):
        """Initialize calendar service"""
        self.db = db_manager
        self.credentials_file = os.getenv('GOOGLE_CREDENTIALS_FILE', 'credentials.json')

    def get_auth_url(self, user_id: int) -> Optional[str]:
        """
        Generate OAuth URL for user to authorize calendar access

        Args:
            user_id: Telegram user ID

        Returns:
            Authorization URL or None if error
        """
        try:
            flow = Flow.from_client_secrets_file(
                self.credentials_file,
                scopes=self.SCOPES,
                redirect_uri=self.REDIRECT_URI
            )

            auth_url, state = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                prompt='consent'
            )

            # Store state for verification
            self.db.save_oauth_state(user_id, state)

            return auth_url

        except Exception as e:
            logger.error(f"Error generating auth URL: {e}")
            return None

    def exchange_code_for_tokens(self, code: str, user_id: int) -> bool:
        """
        Exchange authorization code for access tokens

        Args:
            code: Authorization code from callback
            user_id: Telegram user ID

        Returns:
            True if successful, False otherwise
        """
        try:
            flow = Flow.from_client_secrets_file(
                self.credentials_file,
                scopes=self.SCOPES,
                redirect_uri=self.REDIRECT_URI
            )

            flow.fetch_token(code=code)
            credentials = flow.credentials

            # Save tokens to database
            tokens = {
                'token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': credentials.scopes
            }

            return self.db.save_calendar_tokens(user_id, json.dumps(tokens))

        except Exception as e:
            logger.error(f"Error exchanging code for tokens: {e}")
            return False

    def get_credentials(self, user_id: int) -> Optional[Credentials]:
        """
        Get valid credentials for user

        Args:
            user_id: Telegram user ID

        Returns:
            Valid Credentials object or None
        """
        try:
            tokens_json = self.db.get_calendar_tokens(user_id)
            if not tokens_json:
                return None

            tokens = json.loads(tokens_json)
            credentials = Credentials(
                token=tokens['token'],
                refresh_token=tokens.get('refresh_token'),
                token_uri=tokens['token_uri'],
                client_id=tokens['client_id'],
                client_secret=tokens['client_secret'],
                scopes=tokens['scopes']
            )

            # Refresh if expired
            if credentials.expired and credentials.refresh_token:
                from google.auth.transport.requests import Request
                credentials.refresh(Request())

                # Update stored tokens
                new_tokens = {
                    'token': credentials.token,
                    'refresh_token': credentials.refresh_token,
                    'token_uri': credentials.token_uri,
                    'client_id': credentials.client_id,
                    'client_secret': credentials.client_secret,
                    'scopes': credentials.scopes
                }
                self.db.save_calendar_tokens(user_id, json.dumps(new_tokens))

            return credentials

        except Exception as e:
            logger.error(f"Error getting credentials: {e}")
            return None

    def is_connected(self, user_id: int) -> bool:
        """Check if user has connected calendar"""
        return self.db.get_calendar_tokens(user_id) is not None

    def disconnect(self, user_id: int) -> bool:
        """Disconnect user's calendar"""
        return self.db.delete_calendar_tokens(user_id)

    def sync_task_to_calendar(self, user_id: int, task_id: int) -> Optional[str]:
        """
        Sync a task to Google Calendar

        Args:
            user_id: Telegram user ID
            task_id: Task ID to sync

        Returns:
            Calendar event ID or None if error
        """
        try:
            credentials = self.get_credentials(user_id)
            if not credentials:
                return None

            task = self.db.get_task(task_id, user_id)
            if not task:
                return None

            service = build('calendar', 'v3', credentials=credentials)

            # Prepare event
            event = {
                'summary': task.title,
                'description': f"Task from SmartLife Bot\nPriority: {task.priority}\nCategory: {task.category}",
                'start': {
                    'dateTime': task.deadline.isoformat(),
                    'timeZone': os.getenv('TIMEZONE', 'UTC'),
                },
                'end': {
                    'dateTime': (task.deadline + timedelta(hours=1)).isoformat(),
                    'timeZone': os.getenv('TIMEZONE', 'UTC'),
                },
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'popup', 'minutes': 30},
                    ],
                },
            }

            # Create event
            created_event = service.events().insert(
                calendarId='primary',
                body=event
            ).execute()

            event_id = created_event.get('id')

            # Save event ID to task
            self.db.update_task_calendar_event(task_id, event_id)

            return event_id

        except HttpError as e:
            logger.error(f"Calendar API error: {e}")
            return None
        except Exception as e:
            logger.error(f"Error syncing task to calendar: {e}")
            return None

    def update_calendar_event(self, user_id: int, task_id: int) -> bool:
        """
        Update existing calendar event for task

        Args:
            user_id: Telegram user ID
            task_id: Task ID

        Returns:
            True if successful
        """
        try:
            credentials = self.get_credentials(user_id)
            if not credentials:
                return False

            task = self.db.get_task(task_id, user_id)
            if not task or not task.calendar_event_id:
                return False

            service = build('calendar', 'v3', credentials=credentials)

            # Get existing event
            event = service.events().get(
                calendarId='primary',
                eventId=task.calendar_event_id
            ).execute()

            # Update event
            event['summary'] = task.title
            event['start'] = {
                'dateTime': task.deadline.isoformat(),
                'timeZone': os.getenv('TIMEZONE', 'UTC'),
            }
            event['end'] = {
                'dateTime': (task.deadline + timedelta(hours=1)).isoformat(),
                'timeZone': os.getenv('TIMEZONE', 'UTC'),
            }

            service.events().update(
                calendarId='primary',
                eventId=task.calendar_event_id,
                body=event
            ).execute()

            return True

        except Exception as e:
            logger.error(f"Error updating calendar event: {e}")
            return False

    def delete_calendar_event(self, user_id: int, task_id: int) -> bool:
        """
        Delete calendar event for task

        Args:
            user_id: Telegram user ID
            task_id: Task ID

        Returns:
            True if successful
        """
        try:
            credentials = self.get_credentials(user_id)
            if not credentials:
                return False

            task = self.db.get_task(task_id, user_id)
            if not task or not task.calendar_event_id:
                return False

            service = build('calendar', 'v3', credentials=credentials)

            service.events().delete(
                calendarId='primary',
                eventId=task.calendar_event_id
            ).execute()

            # Clear event ID from task
            self.db.update_task_calendar_event(task_id, None)

            return True

        except Exception as e:
            logger.error(f"Error deleting calendar event: {e}")
            return False

    def get_upcoming_events(self, user_id: int, days: int = 7) -> List[Dict]:
        """
        Get upcoming calendar events

        Args:
            user_id: Telegram user ID
            days: Number of days to look ahead

        Returns:
            List of event dictionaries
        """
        try:
            credentials = self.get_credentials(user_id)
            if not credentials:
                return []

            service = build('calendar', 'v3', credentials=credentials)

            # Get events
            now = datetime.utcnow().isoformat() + 'Z'
            max_time = (datetime.utcnow() + timedelta(days=days)).isoformat() + 'Z'

            events_result = service.events().list(
                calendarId='primary',
                timeMin=now,
                timeMax=max_time,
                maxResults=50,
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            events = events_result.get('items', [])

            return events

        except Exception as e:
            logger.error(f"Error getting calendar events: {e}")
            return []

    def find_free_slots(self, user_id: int, duration_hours: int = 1, days_ahead: int = 7) -> List[Dict]:
        """
        Find free time slots in calendar

        Args:
            user_id: Telegram user ID
            duration_hours: Required duration in hours
            days_ahead: How many days to look ahead

        Returns:
            List of free slot dictionaries with 'start' and 'end' times
        """
        try:
            events = self.get_upcoming_events(user_id, days_ahead)

            # Convert to busy times
            busy_times = []
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                end = event['end'].get('dateTime', event['end'].get('date'))
                busy_times.append({
                    'start': datetime.fromisoformat(start.replace('Z', '+00:00')),
                    'end': datetime.fromisoformat(end.replace('Z', '+00:00'))
                })

            # Find free slots (9 AM - 6 PM on weekdays)
            free_slots = []
            current_date = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
            end_date = current_date + timedelta(days=days_ahead)

            while current_date < end_date:
                # Skip weekends
                if current_date.weekday() >= 5:
                    current_date += timedelta(days=1)
                    continue

                # Check each hour slot
                work_start = current_date.replace(hour=9)
                work_end = current_date.replace(hour=18)

                slot_start = work_start
                while slot_start + timedelta(hours=duration_hours) <= work_end:
                    slot_end = slot_start + timedelta(hours=duration_hours)

                    # Check if slot overlaps with busy times
                    is_free = True
                    for busy in busy_times:
                        if (slot_start < busy['end'] and slot_end > busy['start']):
                            is_free = False
                            break

                    if is_free:
                        free_slots.append({
                            'start': slot_start,
                            'end': slot_end
                        })

                    slot_start += timedelta(hours=1)

                current_date += timedelta(days=1)

            return free_slots[:10]  # Return top 10 slots

        except Exception as e:
            logger.error(f"Error finding free slots: {e}")
            return []