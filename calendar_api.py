import os.path
import datetime
import logging
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar.events"]

class GoogleCalendarIntegrator:
    def __init__(self):
        self.creds = None
        self.token_path = "token.json"
        self.credentials_path = "credentials.json"
        self._authenticate()

    def _authenticate(self):
        """Handles the OAuth2 flow."""
        if os.path.exists(self.token_path):
            self.creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
        
        # If there are no (valid) credentials available, let the user log in.
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                try:
                    self.creds.refresh(Request())
                except Exception as e:
                    logging.error(f"Error refreshing Google token: {e}")
                    self._run_new_flow()
            else:
                self._run_new_flow()

    def _run_new_flow(self):
        """Runs the interactive flow to get new credentials."""
        if not os.path.exists(self.credentials_path):
            logging.error("credentials.json not found. Please follow instructions in implementation_plan.md")
            return

        flow = InstalledAppFlow.from_client_secrets_file(self.credentials_path, SCOPES)
        # Note: This will open a browser window or provide a link in the console.
        # In a headless environment, this might need more configuration.
        self.creds = flow.run_local_server(port=0)
        
        # Save the credentials for the next run
        with open(self.token_path, "w") as token:
            token.write(self.creds.to_json())

    def get_today_events(self):
        """Returns events for the current day."""
        if not self.creds:
            return []

        try:
            service = build("calendar", "v3", credentials=self.creds)

            # Call the Calendar API
            now = datetime.datetime.utcnow().isoformat() + "Z"  # 'Z' indicates UTC time
            end_of_day = (datetime.datetime.utcnow().replace(hour=23, minute=59, second=59)).isoformat() + "Z"
            
            logging.info(f"Fetching events from {now} to {end_of_day}")
            events_result = (
                service.events()
                .list(
                    calendarId="primary",
                    timeMin=now,
                    timeMax=end_of_day,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
            events = events_result.get("items", [])

            formatted_events = []
            for event in events:
                start = event["start"].get("dateTime", event["start"].get("date"))
                # Clean up ISO format for readability (e.g. 2024-03-17T10:00:00+03:00 -> 10:00)
                if "T" in start:
                    time_str = start.split("T")[1][:5]
                else:
                    time_str = "All Day"
                
                formatted_events.append({
                    "time": time_str,
                    "summary": event.get("summary", "No Title")
                })
            
            return formatted_events

        except HttpError as error:
            logging.error(f"An error occurred with Google Calendar API: {error}")
            return []
        except Exception as e:
            logging.error(f"Unexpected error in calendar integration: {e}")
            return []

    def get_week_events(self):
        """Returns events for the next 7 days."""
        if not self.creds:
            return []

        try:
            service = build("calendar", "v3", credentials=self.creds)

            now = datetime.datetime.utcnow().isoformat() + "Z"
            # 7 days from now
            one_week_later = (datetime.datetime.utcnow() + datetime.timedelta(days=7)).replace(hour=23, minute=59, second=59).isoformat() + "Z"
            
            logging.info(f"Fetching events from {now} to {one_week_later}")
            events_result = (
                service.events()
                .list(
                    calendarId="primary",
                    timeMin=now,
                    timeMax=one_week_later,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
            events = events_result.get("items", [])

            formatted_events = []
            for event in events:
                start = event["start"].get("dateTime", event["start"].get("date"))
                date_str = start.split("T")[0] if "T" in start else start
                time_str = start.split("T")[1][:5] if "T" in start else "All Day"
                
                formatted_events.append({
                    "date": date_str,
                    "time": time_str,
                    "summary": event.get("summary", "No Title")
                })
            
            return formatted_events

        except HttpError as error:
            logging.error(f"An error occurred with Google Calendar API: {error}")
            return []
        except Exception as e:
            logging.error(f"Unexpected error in calendar integration: {e}")
            return []

    def add_event(self, summary, start_time, end_time=None, description=None):
        """Creates an event in the primary calendar."""
        if not self.creds:
            return None

        try:
            service = build("calendar", "v3", credentials=self.creds)
            
            # If end_time is not provided, making it 1 hour after start_time
            if not end_time:
                start_dt = datetime.datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                end_dt = start_dt + datetime.timedelta(hours=1)
                end_time = end_dt.isoformat()

            event = {
                'summary': summary,
                'description': description,
                'start': {
                    'dateTime': start_time,
                    'timeZone': 'UTC', # Or user's timezone if known
                },
                'end': {
                    'dateTime': end_time,
                    'timeZone': 'UTC',
                },
            }

            event = service.events().insert(calendarId='primary', body=event).execute()
            logging.info(f"Event created: {event.get('htmlLink')}")
            return event

        except HttpError as error:
            logging.error(f"An error occurred while creating event: {error}")
            return None
        except Exception as e:
            logging.error(f"Unexpected error in add_event: {e}")
            return None

if __name__ == "__main__":
    # Test script
    logging.basicConfig(level=logging.INFO)
    integrator = GoogleCalendarIntegrator()
    events = integrator.get_today_events()
    print("Today's events:")
    for e in events:
        print(f"- {e['time']}: {e['summary']}")
