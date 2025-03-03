from icalendar import Calendar, Event
from datetime import datetime, timedelta
import pytz
import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Google Calendar API scopes
SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_db_connection():
    """Get database connection using environment variables"""
    return psycopg2.connect(
        host=os.getenv("PGHOST","aws-0-eu-central-1.pooler.supabase.com"),
        database=os.getenv("PGDATABASE","postgres"),
        user=os.getenv("PGUSER","postgres.lvonpafzqjfxqenzvjth"),
        password=os.getenv("PGPASSWORD","trtrtr123"),
        port=os.getenv("PGPORT","5432")
    )

def generate_ical_calendar(user_id, user_role="student"):
    """Generate iCal format calendar for a specific user"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Query based on user role
        if user_role == "student":
            cur.execute("""
                SELECT * FROM schedules 
                WHERE student = %s
                ORDER BY date_time
            """, (user_id,))
        else:  # professor
            cur.execute("""
                SELECT * FROM schedules 
                WHERE president = %s 
                OR rapporteur = %s 
                OR supervisor = %s
                ORDER BY date_time
            """, (user_id, user_id, user_id))

        presentations = cur.fetchall()

        # Create calendar
        cal = Calendar()
        cal.add('prodid', '-//PFE Schedule Manager//EN')
        cal.add('version', '2.0')

        for presentation in presentations:
            event = Event()

            # Set event details
            event.add('summary', f"PFE Presentation: {presentation['student']}")
            event.add('dtstart', presentation['date_time'])
            event.add('dtend', presentation['date_time'] + timedelta(hours=1))
            event.add('location', presentation['room'])

            # Add description with all details
            description = f"""
            Student: {presentation['student']}
            Topic: {presentation['topic']}
            Room: {presentation['room']}
            Jury:
            - President: {presentation['president']}
            - Rapporteur: {presentation['rapporteur']}
            - Supervisor: {presentation['supervisor']}
            """
            event.add('description', description)

            # Add to calendar
            cal.add_component(event)

        cur.close()
        conn.close()

        return cal.to_ical()

    except Exception as e:
        logger.error(f"Error generating iCal calendar: {str(e)}")
        raise

def export_to_google_calendar(presentation_data, credentials=None):
    """Export a presentation to Google Calendar"""
    try:
        creds = None

        # Check if we have valid credentials
        if credentials:
            creds = Credentials.from_authorized_user_info(credentials, SCOPES)

        # If credentials invalid or don't exist, prompt for new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)

        # Build Google Calendar service
        service = build('calendar', 'v3', credentials=creds)

        # Create event
        event = {
            'summary': f"PFE Presentation: {presentation_data['Student']}",
            'location': presentation_data['Room'],
            'description': f"""
            Topic: {presentation_data['Topic']}
            Student: {presentation_data['Student']}
            Room: {presentation_data['Room']}
            President: {presentation_data['President']}
            Rapporteur: {presentation_data['Rapporteur']}
            Supervisor: {presentation_data['Supervisor']}
            """,
            'start': {
                'dateTime': presentation_data['Date & Time'],
                'timeZone': 'Africa/Tunis',
            },
            'end': {
                'dateTime': (datetime.strptime(presentation_data['Date & Time'], '%Y-%m-%d %H:%M') + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M'),
                'timeZone': 'Africa/Tunis',
            },
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 24 * 60},
                    {'method': 'popup', 'minutes': 60},
                ],
            },
        }

        # Insert event
        event = service.events().insert(calendarId='primary', body=event).execute()
        logger.info(f"Event created: {event.get('htmlLink')}")

        return True, event.get('htmlLink')

    except Exception as e:
        logger.error(f"Error exporting to Google Calendar: {str(e)}")
        return False, str(e)