import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Email configuration
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

# Database configuration
DB_HOST = os.getenv("PGHOST", "aws-0-eu-central-1.pooler.supabase.com")
DB_NAME = os.getenv("PGDATABASE", "postgres")
DB_USER = os.getenv("PGUSER", "postgres.lvonpafzqjfxqenzvjth")
DB_PASSWORD = os.getenv("PGPASSWORD", "trtrtr123")
DB_PORT = os.getenv("PGPORT", "5432")

def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT
    )

def send_email(recipient_email, subject, body):
    """Send an email using SMTP"""
    try:
        msg = MIMEMultipart()
        msg['From'] = SMTP_USERNAME
        msg['To'] = recipient_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'plain'))
        
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
            
        logger.info(f"Email sent successfully to {recipient_email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}")
        return False

def send_schedule_notification(presentation, recipients):
    """Send a notification about a scheduled presentation"""
    subject = f"PFE Presentation Scheduled: {presentation['student']}"
    
    body = f"""
    Dear participant,

    A PFE presentation has been scheduled with the following details:

    Student: {presentation['student']}
    Topic: {presentation['topic']}
    Date: {presentation['date_time'].strftime('%Y-%m-%d %H:%M')}
    Room: {presentation['room']}

    Jury Members:
    - President: {presentation['president']}
    - Rapporteur: {presentation['rapporteur']}
    - Supervisor: {presentation['supervisor']}

    Please make sure to arrive on time.

    Best regards,
    PFE Schedule Manager
    """
    
    for recipient in recipients:
        send_email(recipient, subject, body)

def send_reminder(presentation, recipients, hours_before):
    """Send a reminder before the presentation"""
    subject = f"Reminder: PFE Presentation - {presentation['student']}"
    
    body = f"""
    Dear participant,

    This is a reminder for the upcoming PFE presentation:

    Student: {presentation['student']}
    Topic: {presentation['topic']}
    Date: {presentation['date_time'].strftime('%Y-%m-%d %H:%M')}
    Room: {presentation['room']}

    The presentation will start in {hours_before} hours.

    Best regards,
    PFE Schedule Manager
    """
    
    for recipient in recipients:
        send_email(recipient, subject, body)

def check_upcoming_presentations():
    """Check for upcoming presentations and send reminders"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Get presentations in the next 24 hours
    cur.execute("""
        SELECT * FROM schedules 
        WHERE date_time BETWEEN NOW() AND NOW() + INTERVAL '24 hours'
        ORDER BY date_time
    """)
    
    upcoming = cur.fetchall()
    
    for presentation in upcoming:
        time_until = presentation['date_time'] - datetime.now()
        hours_until = time_until.total_seconds() / 3600
        
        recipients = [
            presentation['student_email'],
            presentation['supervisor_email'],
            presentation['president_email'],
            presentation['rapporteur_email']
        ]
        
        # Send reminders at different intervals
        if 23 <= hours_until <= 24:  # 24-hour reminder
            send_reminder(presentation, recipients, 24)
        elif 3 <= hours_until <= 4:  # 4-hour reminder
            send_reminder(presentation, recipients, 4)
        elif 0.75 <= hours_until <= 1:  # 1-hour reminder
            send_reminder(presentation, recipients, 1)
    
    cur.close()
    conn.close()
