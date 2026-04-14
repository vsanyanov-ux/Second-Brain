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
        """Runs the flow to get new credentials. Headless-friendly."""
        if not os.path.exists(self.credentials_path):
            logging.error("credentials.json not found. Please follow instructions in implementation_plan.md")
            return

        flow = InstalledAppFlow.from_client_secrets_file(self.credentials_path, SCOPES)
        
        # HEADLESS FIX: Don't open browser, just print the URL.
        # User will need to check Docker logs and copy the URL.
        logging.info("Running headless auth flow. CHECK DOCKER LOGS FOR URL.")
        try:
            # This will still try to run a local server but won't try to open a browser.
            # We use port 0 to find a free one, but the user might not be able to reach it 
            # if they aren't port-forwarding. 
            # A simpler way is to use 'console' flow if it were available, 
            # but here we'll just catch the error or guide the user.
            self.creds = flow.run_local_server(port=0, open_browser=False)
            
            # Save the credentials for the next run
            with open(self.token_path, "w") as token:
                token.write(self.creds.to_json())
            logging.info(f"Successfully saved new token to {self.token_path}")
        except Exception as e:
            logging.error(f"Failed to run auth flow: {e}")
            logging.error("In a headless VPS, you might need to run this locally first and scp token.json to the server.")

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
            logging.error("No credentials available for add_event")
            return None

        if not start_time:
            logging.error(f"Cannot create event '{summary}' without start_time")
            return None

        try:
            service = build("calendar", "v3", credentials=self.creds)
            
            # Helper to ensure offset is present for Google API
            def ensure_offset(dt_str):
                if not dt_str: return None
                # Check for T and absence of offset/Z
                if "T" in dt_str and "+" not in dt_str and "-" not in dt_str[dt_str.find("T"):] and "Z" not in dt_str:
                    # Append Moscow offset if missing (user's timezone)
                    return dt_str + "+03:00"
                return dt_str

            # Normalize start_time
            start_time = ensure_offset(start_time)

            # If end_time is not provided, making it 1 hour after start_time
            if not end_time:
                # Parse start_time to calculate end_time
                try:
                    # Clean Z for fromisoformat if needed
                    parse_str = start_time.replace('Z', '+00:00')
                    start_dt = datetime.datetime.fromisoformat(parse_str)
                    end_dt = start_dt + datetime.timedelta(hours=1)
                    end_time = end_dt.isoformat()
                except Exception as parse_err:
                    logging.warning(f"Could not parse start_time '{start_time}': {parse_err}")
                    # Fallback: end time same as start time if parsing fails
                    end_time = start_time
            else:
                end_time = ensure_offset(end_time)

            event = {
                'summary': summary,
                'description': description,
                'start': {
                    'dateTime': start_time,
                    'timeZone': 'Europe/Moscow',
                },
                'end': {
                    'dateTime': end_time,
                    'timeZone': 'Europe/Moscow',
                },
            }

            logging.info(f"Adding event: {summary} at {start_time}")
            event = service.events().insert(calendarId='primary', body=event).execute()
            logging.info(f"Event created: {event.get('htmlLink')}")
            return event

        except HttpError as error:
            error_details = error.content.decode()
            logging.error(f"An error occurred while creating event: {error_details}")
            raise Exception(f"Google Calendar API Error: {error_details}")
        except Exception as e:
            logging.error(f"Unexpected error in add_event: {e}", exc_info=True)
            raise e

if __name__ == "__main__":
    # Test script
    logging.basicConfig(level=logging.INFO)
    integrator = GoogleCalendarIntegrator()
    events = integrator.get_today_events()
    print("Today's events:")
    for e in events:
        print(f"- {e['time']}: {e['summary']}")
