# Moving analytics.py content to attached_assets directory
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import datetime, timedelta
import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def display_analytics_dashboard():
    """Display analytics dashboard with project statistics"""
    st.title("Analytics Dashboard")

    # Get database connection
    conn = psycopg2.connect(
        host=os.getenv("PGHOST","aws-0-eu-central-1.pooler.supabase.com"),
        database=os.getenv("PGDATABASE","postgres"),
        user=os.getenv("PGUSER","postgres.lvonpafzqjfxqenzvjth"),
        password=os.getenv("PGPASSWORD","trtrtr123"),
        port=os.getenv("PGPORT","5432")
    )
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Query schedule data
    cur.execute("""
        SELECT date_time, topic, student, room, president, rapporteur, supervisor
        FROM schedules
        ORDER BY date_time
    """)
    schedule_data = cur.fetchall()

    if not schedule_data:
        st.info("No schedule data available for analysis.")
        return

    # Convert to DataFrame
    df = pd.DataFrame(schedule_data)

    # Get department data using project classifier
    from project_classifier import classifier
    df['department'] = df['topic'].apply(classifier.classify_project)

    # Projects per Department
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Projects by Department")
        dept_counts = df.groupby("department").size().reset_index(name="count")
        fig_dept = px.pie(dept_counts, values="count", names="department")
        st.plotly_chart(fig_dept)

    with col2:
        st.subheader("Presentations per Room")
        room_counts = df.groupby("room").size().reset_index(name="count")
        fig_room = px.bar(room_counts, x="room", y="count")
        st.plotly_chart(fig_room)

    # Timeline of Presentations
    st.subheader("Presentation Timeline")
    df["date"] = pd.to_datetime(df["date_time"]).dt.date
    timeline_data = df.groupby("date").size().reset_index(name="presentations")
    fig_timeline = px.line(timeline_data, x="date", y="presentations",
                          title="Number of Presentations per Day")
    st.plotly_chart(fig_timeline)

    # Supervisor Statistics
    st.subheader("Supervisor Statistics")
    supervisor_counts = df.groupby("supervisor").size().reset_index(name="projects")
    supervisor_counts = supervisor_counts.sort_values("projects", ascending=False)
    fig_supervisor = px.bar(supervisor_counts, x="supervisor", y="projects",
                           title="Projects per Supervisor")
    st.plotly_chart(fig_supervisor)

    # Jury Member Activity
    st.subheader("Jury Member Activity")
    jury_data = pd.concat([
        df["president"].value_counts().rename("As President"),
        df["rapporteur"].value_counts().rename("As Rapporteur")
    ], axis=1).fillna(0)

    jury_data["Total"] = jury_data["As President"] + jury_data["As Rapporteur"]
    jury_data = jury_data.sort_values("Total", ascending=False)

    fig_jury = go.Figure(data=[
        go.Bar(name="As President", x=jury_data.index, y=jury_data["As President"]),
        go.Bar(name="As Rapporteur", x=jury_data.index, y=jury_data["As Rapporteur"])
    ])
    fig_jury.update_layout(barmode="stack", title="Jury Member Participation")
    st.plotly_chart(fig_jury)

    # Close database connection
    cur.close()
    conn.close()