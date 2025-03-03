import streamlit as st
st.set_page_config(page_title="PFE Schedule Manager", layout="wide")

import pandas as pd
from datetime import datetime, timedelta
import tempfile
import os
import io
import plotly.graph_objects as go
import psycopg2
from psycopg2.extras import RealDictCursor
import json
from dotenv import load_dotenv
import logging

# Import local modules using absolute imports 
from pfescheduler import PFEScheduler
from google_forms import create_student_form
from analytics import display_analytics_dashboard
from calendar_integration import generate_ical_calendar, export_to_google_calendar
from notification_system import send_schedule_notification
from room_management import display_room_management
from project_classifier import classifier

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Database configuration
DB_HOST = os.getenv("PGHOST", "aws-0-eu-central-1.pooler.supabase.com")
DB_NAME = os.getenv("PGDATABASE", "postgres")
DB_USER = os.getenv("PGUSER", "postgres.lvonpafzqjfxqenzvjth")
DB_PASSWORD = os.getenv("PGPASSWORD", "trtrtr123")
DB_PORT = os.getenv("PGPORT", "5432")

def get_db_connection():
    try:
        return psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT
        )
    except Exception as e:
        st.error(f"Failed to connect to database: {str(e)}")
        logger.error(f"Database connection error: {str(e)}")
        raise

def init_database():
    conn = get_db_connection()
    cur = conn.cursor()

    # Create tables if they don't exist
    cur.execute("""
        CREATE TABLE IF NOT EXISTS schedules (
            id SERIAL PRIMARY KEY,
            date_time TIMESTAMP,
            topic TEXT,
            student TEXT,
            room TEXT,
            president TEXT,
            rapporteur TEXT,
            supervisor TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Add student_submissions table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS student_submissions (
            id SERIAL PRIMARY KEY,
            full_name TEXT NOT NULL,
            email TEXT NOT NULL,
            project_title TEXT NOT NULL,
            supervisor TEXT NOT NULL,
            submission_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    cur.close()
    conn.close()

def save_schedule_to_db(schedule_data):
    conn = get_db_connection()
    cur = conn.cursor()

    # Clear existing schedule
    cur.execute("DELETE FROM schedules")

    # Insert new schedule
    for item in schedule_data:
        cur.execute("""
            INSERT INTO schedules 
            (date_time, topic, student, room, president, rapporteur, supervisor)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            datetime.strptime(item['Date & Time'], '%Y-%m-%d %H:%M'),
            item['Topic'],
            item['Student'],
            item['Room'],
            item['President'],
            item['Rapporteur'],
            item['Supervisor']
        ))

    conn.commit()
    cur.close()
    conn.close()

def load_schedule_from_db():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT * FROM schedules 
        ORDER BY date_time
    """)

    rows = cur.fetchall()
    cur.close()
    conn.close()

    if rows:
        schedule_data = []
        for row in rows:
            schedule_data.append({
                'date': row['date_time'].strftime('%Y-%m-%d %H:%M'),
                'topic': row['topic'],
                'student': row['student'],
                'room': row['room'],
                'jury': [
                    {'role': 'President', 'name': row['president']},
                    {'role': 'Rapporteur', 'name': row['rapporteur']},
                    {'role': 'Supervisor', 'name': row['supervisor']}
                ]
            })
        return schedule_data
    return None

def show_professor_schedule():
    st.title(f"Professor Schedule - {st.session_state.user_id}")

    schedule_data = load_schedule_from_db()
    if schedule_data is not None:
        professor_schedule = []
        for item in schedule_data:
            for jury_member in item['jury']:
                if jury_member['name'].strip() == st.session_state.user_id.strip():
                    professor_schedule.append({
                        'Date & Time': item['date'],
                        'Role': jury_member['role'],
                        'Student': item['student'],
                        'Topic': item['topic'],
                        'Room': item['room']
                    })
                    break

        if professor_schedule:
            df = pd.DataFrame(professor_schedule)
            st.dataframe(df, use_container_width=True)

            # Add calendar export options
            st.subheader("Export Calendar")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Export to iCal"):
                    ical_data = generate_ical_calendar(
                        user_id=st.session_state.user_id,
                        user_role="professor"
                    )
                    st.download_button(
                        "Download iCal File",
                        data=ical_data,
                        file_name="professor_schedule.ics",
                        mime="text/calendar"
                    )

            with col2:
                if st.button("Export to Google Calendar"):
                    success, message = export_to_google_calendar(
                        professor_schedule[0],  # Export first presentation
                        None  # Add credentials handling
                    )
                    if success:
                        st.success("Successfully exported to Google Calendar")
                    else:
                        st.error(f"Failed to export: {message}")
        else:
            st.info(f"No scheduled presentations found for professor {st.session_state.user_id}")
    else:
        st.info("Schedule has not been generated yet.")

def show_student_schedule():
    st.title(f"Student Schedule - {st.session_state.user_id}")

    schedule_data = load_schedule_from_db()
    if schedule_data is not None:
        student_schedule = []
        for item in schedule_data:
            if str(item['student']).strip() == str(st.session_state.user_id).strip():
                jury_dict = {j['role']: j['name'] for j in item['jury']}
                student_schedule.append({
                    'Date & Time': item['date'],
                    'Topic': item['topic'],
                    'Room': item['room'],
                    'President': jury_dict['President'],
                    'Rapporteur': jury_dict['Rapporteur'],
                    'Supervisor': jury_dict['Supervisor']
                })

        if student_schedule:
            df = pd.DataFrame(student_schedule)
            st.dataframe(df, use_container_width=True)

            # Add calendar export options
            st.subheader("Export Calendar")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Export to iCal"):
                    ical_data = generate_ical_calendar(
                        user_id=st.session_state.user_id,
                        user_role="student"
                    )
                    st.download_button(
                        "Download iCal File",
                        data=ical_data,
                        file_name="student_schedule.ics",
                        mime="text/calendar"
                    )

            with col2:
                if st.button("Export to Google Calendar"):
                    success, message = export_to_google_calendar(
                        student_schedule[0],  # Export first presentation
                        None  # Add credentials handling
                    )
                    if success:
                        st.success("Successfully exported to Google Calendar")
                    else:
                        st.error(f"Failed to export: {message}")
        else:
            st.info(f"No scheduled presentation found for student {st.session_state.user_id}")
    else:
        st.info("Schedule has not been generated yet.")

def show_schedule_management():
    # Load existing schedule if available
    existing_schedule = load_schedule_from_db()
    if existing_schedule:
        st.subheader("Current Schedule")
        formatted_schedule = []
        for item in existing_schedule:
            jury_dict = {j['role']: j['name'] for j in item['jury']}
            formatted_schedule.append({
                'Date & Time': item['date'],
                'Topic': item['topic'],
                'Student': item['student'],
                'Room': item['room'],
                'President': jury_dict['President'],
                'Rapporteur': jury_dict['Rapporteur'],
                'Supervisor': jury_dict['Supervisor']
            })
        current_schedule_df = pd.DataFrame(formatted_schedule)
        st.dataframe(current_schedule_df, use_container_width=True)

    # File upload
    uploaded_file = st.file_uploader("Choose an Excel file", type="xlsx")

    if uploaded_file is not None:
        # Read Excel file
        df = pd.read_excel(uploaded_file)

        # Add department classification
        df['Departement'] = df['codeSujet'].apply(classifier.classify_project)

        # Display data by department
        st.subheader("Projects by Department")
        departments = df['Departement'].unique()

        for dept in departments:
            with st.expander(f"{dept} Projects"):
                dept_df = df[df['Departement'] == dept]
                st.dataframe(dept_df)

                # Count of projects per department
                st.metric(f"Total {dept} Projects", len(dept_df))

        # Display the overall imported data
        st.subheader("All Imported Data")
        st.dataframe(df)

        # Initialize scheduler
        scheduler = PFEScheduler()

        # Add presentations from Excel data
        for _, row in df.iterrows():
            scheduler.add_presentation(
                topic=row['Sujet'],
                student=f"{row['Nom']} {row['Prénom']}",
                supervisor=row['Encadrant']
            )

        # Date selection
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start Date", datetime.now())
        with col2:
            days = st.number_input("Number of Days", min_value=1, value=2)

        slots_per_day = st.number_input("Presentations per Day", min_value=1, value=4)

        # Professor availability section
        st.subheader("Professor Availability Constraints")

        # Add new constraint section
        st.write("Add new availability constraint:")
        constraint_cols = st.columns([2, 2, 2, 1])

        with constraint_cols[0]:
            professors = df['Encadrant'].unique()
            selected_professor = st.selectbox(
                "Select Professor",
                options=list(professors)
            )

        with constraint_cols[1]:
            date_options = [start_date + timedelta(days=x) for x in range(days)]
            selected_dates = st.multiselect(
                "Select Dates",
                options=date_options,
                format_func=lambda x: x.strftime('%Y-%m-%d (%A)')
            )

        with constraint_cols[2]:
            st.write()
            time_range = st.slider(
                "Select Time Range",
                min_value=9,
                max_value=9 + slots_per_day - 1,
                value=(9, 9 + slots_per_day - 1),
                step=1,
                format="%d:00"
            )

        with constraint_cols[3]:
            if st.button("Add Constraint"):
                for selected_date in selected_dates:
                    for hour in range(time_range[0], time_range[1] + 1):
                        constraint_datetime = datetime.combine(
                            selected_date,
                            datetime.strptime(f"{hour:02d}:00", "%H:%M").time()
                        )
                        constraint_key = f"{selected_professor}_{constraint_datetime}"
                        st.session_state.constraints[constraint_key] = {
                            'professor': selected_professor,
                            'datetime': constraint_datetime
                        }
                st.experimental_rerun()

        # Display current constraints
        if st.session_state.constraints:
            st.write("Current Constraints:")
            constraints_data = []
            for key, constraint in st.session_state.constraints.items():
                constraints_data.append({
                    'Professor': constraint['professor'],
                    'Date': constraint['datetime'].strftime('%Y-%m-%d'),
                    'Time': constraint['datetime'].strftime('%H:%M')
                })

            constraints_df = pd.DataFrame(constraints_data)

            col1, col2 = st.columns([3, 1])
            with col1:
                st.dataframe(constraints_df, use_container_width=True)
            with col2:
                if st.button("Clear All Constraints"):
                    st.session_state.constraints = {}
                    st.rerun()

        if st.button("Generate Schedule"):
            try:
                # Generate time slots
                scheduler.generate_time_slots(
                    start_date.strftime('%Y-%m-%d'),
                    days,
                    slots_per_day
                )

                # Set professor unavailability from constraints
                for constraint in st.session_state.constraints.values():
                    scheduler.set_professor_unavailability(
                        constraint['professor'],
                        [constraint['datetime']]
                    )

                # Schedule presentations
                scheduler.schedule_presentations()

                # Get schedule
                schedule = scheduler.export_schedule()

                # Store room usage in session state
                st.session_state.room_usage = scheduler.get_room_usage()

                # Format the schedule data for display and Excel export
                formatted_schedule = []
                for item in schedule:
                    jury_dict = {j['role']: j['name'] for j in item['jury']}
                    formatted_schedule.append({
                        'Date & Time': item['date'],
                        'Topic': item['topic'],
                        'Student': item['student'],
                        'Room': item['room'],
                        'President': jury_dict['President'],
                        'Rapporteur': jury_dict['Rapporteur'],
                        'Supervisor': jury_dict['Supervisor']
                    })

                # Save to database
                save_schedule_to_db(formatted_schedule)

                # Create DataFrame for display
                schedule_df = pd.DataFrame(formatted_schedule)

                # Display schedule
                st.subheader("Generated Schedule")
                st.dataframe(schedule_df)

                # Generate PDF
                pdf_buffer = io.BytesIO()
                scheduler.generate_pdf(pdf_buffer)
                pdf_buffer.seek(0)

                col1, col2, col3 = st.columns([1, 1, 1])
                with col1:
                    # Provide download button for PDF
                    st.download_button(
                        label="Download PDF Schedule",
                        data=pdf_buffer,
                        file_name="pfe_schedule.pdf",
                        mime="application/pdf"
                    )

                with col2:
                    # Provide download button for Excel
                    excel_buffer = io.BytesIO()
                    schedule_df.to_excel(excel_buffer, index=False, engine='openpyxl')
                    excel_buffer.seek(0)

                    st.download_button(
                        label="Download Excel Schedule",
                        data=excel_buffer,
                        file_name="pfe_schedule.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

                with col3:
                    # Room visualization button
                    st.button("Toggle Room Usage", on_click=toggle_room_modal)

                # Send notifications
                with st.spinner("Sending notifications..."):
                    for schedule_item in formatted_schedule:
                        recipients = [
                            schedule_item['Student'],  # Add proper email addresses
                            schedule_item['President'],
                            schedule_item['Rapporteur'],
                            schedule_item['Supervisor']
                        ]
                        send_schedule_notification(schedule_item, recipients)

                # Success message
                st.success("Schedule has been generated and notifications sent!")

            except Exception as e:
                st.error(f"An error occurred: {str(e)}")

def show_admin_interface():
    st.title("PFE Schedule Manager")

    # Add tabs for different admin functions
    tab1, tab2, tab3, tab4 = st.tabs([
        "Schedule Management",
        "Student Submissions",
        "Analytics Dashboard",
        "Room Management"
    ])

    with tab1:
        show_schedule_management()

    with tab2:
        show_student_submissions()

    with tab3:
        display_analytics_dashboard()

    with tab4:
        display_room_management()

def show_student_submissions():
    st.subheader("Student Form Management")

    if st.button("Generate New Student Form"):
        try:
            form_info = create_student_form()
            st.success(f"New form created successfully!")
            st.markdown(f"Form URL: {form_info['formUrl']}")

            # Store form ID in session state
            st.session_state.current_form_id = form_info['formId']
        except Exception as e:
            st.error(f"Error creating form: {str(e)}")

    # Display submitted data
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT * FROM student_submissions 
        ORDER BY submission_date DESC
    """)

    submissions = cur.fetchall()
    cur.close()
    conn.close()

    if submissions:
        st.subheader("Submitted Student Information")
        df = pd.DataFrame(submissions)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No student submissions yet.")

def toggle_room_modal():
    st.session_state.show_room_modal = not st.session_state.show_room_modal

def login():
    st.title("PFE Schedule Manager - Login")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

        if submitted:
            if username == "admin" and password == "admin":
                st.session_state.logged_in = True
                st.session_state.user_role = "admin"
                st.experimental_rerun()
            elif password == "prof":
                st.session_state.logged_in = True
                st.session_state.user_role = "professor"
                st.session_state.user_id = username
                st.experimental_rerun()
            elif password == "student":
                st.session_state.logged_in = True
                st.session_state.user_role = "student"
                st.session_state.user_id = username
                st.experimental_rerun()
            else:
                st.error("Invalid credentials")

# Initialize session state
if 'constraints' not in st.session_state:
    st.session_state.constraints = {}
if 'show_room_modal' not in st.session_state:
    st.session_state.show_room_modal = False
if 'room_usage' not in st.session_state:
    st.session_state.room_usage = None
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_role' not in st.session_state:
    st.session_state.user_role = None
if 'user_id' not in st.session_state:
    st.session_state.user_id = None

# Initialize database
try:
    init_database()
except Exception as e:
    st.error(f"Database initialization error: {str(e)}")

# Main app logic
if not st.session_state.logged_in:
    login()
else:
    # Add logout button
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.user_role = None
        st.session_state.user_id = None
        st.experimental_rerun()

    # Show appropriate interface based on user role
    if st.session_state.user_role == "admin":
        show_admin_interface()
    elif st.session_state.user_role == "professor":
        show_professor_schedule()
    elif st.session_state.user_role == "student":
        show_student_schedule()