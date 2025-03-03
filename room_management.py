import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def get_db_connection():
    """Get database connection using environment variables"""
    return psycopg2.connect(
        host=os.getenv("PGHOST","aws-0-eu-central-1.pooler.supabase.com"),
        database=os.getenv("PGDATABASE","postgres"),
        user=os.getenv("PGUSER","postgres.lvonpafzqjfxqenzvjth"),
        password=os.getenv("PGPASSWORD","trtrtr123"),
        port=os.getenv("PGPORT","5432")
    )

def display_room_management():
    """Display the room management interface in Streamlit"""
    st.title("Room Management")

    # Tabs for different room management functions
    tab1, tab2, tab3 = st.tabs([
        "Room Configuration",
        "Room Bookings",
        "Room Status"
    ])

    with tab1:
        st.header("Room Configuration")

        # Add new room
        with st.form("add_room_form"):
            col1, col2 = st.columns(2)

            with col1:
                room_id = st.text_input("Room ID (e.g., G01, K02)")
                capacity = st.number_input("Capacity", min_value=1, value=30)

            with col2:
                equipment = st.multiselect(
                    "Available Equipment",
                    options=['projector', 'whiteboard', 'computer', 'video_conference', 'audio_system']
                )

            if st.form_submit_button("Add/Update Room"):
                conn = None
                cur = None
                try:
                    conn = get_db_connection()
                    cur = conn.cursor()

                    cur.execute("""
                        INSERT INTO rooms (room_id, capacity, equipment)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (room_id) 
                        DO UPDATE SET
                            capacity = EXCLUDED.capacity,
                            equipment = EXCLUDED.equipment
                    """, (room_id, capacity, json.dumps(equipment)))

                    conn.commit()
                    st.success("Room configuration updated successfully!")

                except Exception as e:
                    st.error(f"Error: {str(e)}")
                finally:
                    if cur is not None:
                        cur.close()
                    if conn is not None:
                        conn.close()

        # Display existing rooms
        conn = None
        cur = None
        try:
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)

            cur.execute("SELECT * FROM rooms ORDER BY room_id")
            rooms = cur.fetchall()

            if rooms:
                st.subheader("Existing Rooms")
                rooms_df = pd.DataFrame(rooms)
                st.dataframe(rooms_df)

        except Exception as e:
            st.error(f"Error loading rooms: {str(e)}")
        finally:
            if cur is not None:
                cur.close()
            if conn is not None:
                conn.close()

    with tab2:
        st.header("Room Bookings")

        # Add new booking
        with st.form("add_booking_form"):
            col1, col2 = st.columns(2)

            with col1:
                # Get available rooms
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute("SELECT room_id FROM rooms ORDER BY room_id")
                available_rooms = [r[0] for r in cur.fetchall()]
                cur.close()
                conn.close()

                selected_room = st.selectbox("Select Room", available_rooms if available_rooms else ["No rooms available"])
                booking_date = st.date_input("Date")
                start_time = st.time_input("Start Time")
                end_time = st.time_input("End Time")

            with col2:
                event_type = st.selectbox("Event Type", ["PFE Presentation", "Meeting", "Other"])
                attendees = st.number_input("Number of Attendees", min_value=1)
                equipment_needed = st.multiselect(
                    "Required Equipment",
                    options=['projector', 'whiteboard', 'computer', 'video_conference', 'audio_system']
                )

            if st.form_submit_button("Add Booking"):
                start_datetime = datetime.combine(booking_date, start_time)
                end_datetime = datetime.combine(booking_date, end_time)

                conn = None
                cur = None
                try:
                    conn = get_db_connection()
                    cur = conn.cursor()

                    # Check for conflicts
                    cur.execute("""
                        SELECT COUNT(*) FROM room_bookings 
                        WHERE room_id = %s 
                        AND (
                            (start_time <= %s AND end_time > %s)
                            OR (start_time < %s AND end_time >= %s)
                            OR (start_time >= %s AND end_time <= %s)
                        )
                    """, (selected_room, start_datetime, start_datetime, 
                          end_datetime, end_datetime, start_datetime, end_datetime))

                    if cur.fetchone()[0] > 0:
                        st.error("Room is already booked for this time slot")
                    else:
                        cur.execute("""
                            INSERT INTO room_bookings 
                            (room_id, start_time, end_time, event_type, attendees, equipment_needed)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """, (selected_room, start_datetime, end_datetime, 
                              event_type, attendees, json.dumps(equipment_needed)))

                        conn.commit()
                        st.success("Booking added successfully!")

                except Exception as e:
                    st.error(f"Error: {str(e)}")
                finally:
                    if cur is not None:
                        cur.close()
                    if conn is not None:
                        conn.close()

        # Display bookings
        conn = None
        cur = None
        try:
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)

            cur.execute("""
                SELECT * FROM room_bookings 
                WHERE start_time >= CURRENT_DATE 
                ORDER BY start_time
            """)
            bookings = cur.fetchall()

            if bookings:
                st.subheader("Upcoming Bookings")
                bookings_df = pd.DataFrame(bookings)
                st.dataframe(bookings_df)

        except Exception as e:
            st.error(f"Error loading bookings: {str(e)}")
        finally:
            if cur is not None:
                cur.close()
            if conn is not None:
                conn.close()

    with tab3:
        st.header("Room Status")

        # Update room status
        conn = None
        cur = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()

            cur.execute("SELECT room_id FROM rooms ORDER BY room_id")
            available_rooms = [r[0] for r in cur.fetchall()]

            if available_rooms:
                col1, col2 = st.columns(2)

                with col1:
                    selected_room = st.selectbox(
                        "Select Room",
                        available_rooms,
                        key="status_room"
                    )
                    room_status = st.selectbox(
                        "Status",
                        ["available", "maintenance", "out_of_order", "reserved"]
                    )

                with col2:
                    maintenance_date = st.date_input("Maintenance Date") if room_status == "maintenance" else None
                    notes = st.text_area("Notes")

                if st.button("Update Status"):
                    try:
                        cur.execute("""
                            UPDATE rooms 
                            SET status = %s,
                                last_maintenance = %s,
                                notes = %s
                            WHERE room_id = %s
                        """, (room_status, maintenance_date, notes, selected_room))

                        conn.commit()
                        st.success("Room status updated successfully!")

                    except Exception as e:
                        st.error(f"Error updating status: {str(e)}")
            else:
                st.info("No rooms available. Please add rooms first.")

        except Exception as e:
            st.error(f"Error: {str(e)}")
        finally:
            if cur is not None:
                cur.close()
            if conn is not None:
                conn.close()

if __name__ == "__main__":
    display_room_management()