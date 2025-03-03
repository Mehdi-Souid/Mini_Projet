import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime, timedelta
import calendar
import json

def create_calendar_html(year, month, selected_dates):
    cal = calendar.monthcalendar(year, month)
    month_name = calendar.month_name[month]
    
    html = f"""
    <div id="calendar">
        <h3>{month_name} {year}</h3>
        <table>
            <tr><th>Mon</th><th>Tue</th><th>Wed</th><th>Thu</th><th>Fri</th><th>Sat</th><th>Sun</th></tr>
    """
    
    for week in cal:
        html += "<tr>"
        for day in week:
            if day == 0:
                html += "<td></td>"
            else:
                date = f"{year}-{month:02d}-{day:02d}"
                selected = "selected" if date in selected_dates else ""
                html += f'<td class="day {selected}" data-date="{date}">{day}</td>'
        html += "</tr>"
    
    html += """
        </table>
    </div>
    """
    return html

def main():
    st.title("Multi-select Calendar")

    # Initialize session state for selected dates if it doesn't exist
    if 'selected_dates' not in st.session_state:
        st.session_state.selected_dates = set()

    # Date range inputs
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date", datetime.now().date())
    with col2:
        end_date = st.date_input("End Date", start_date + timedelta(days=30))

    # Create calendar HTML
    calendar_html = create_calendar_html(start_date.year, start_date.month, st.session_state.selected_dates)

    # JavaScript for handling date selection
    js = """
    <script>
    const calendar = document.getElementById('calendar');
    calendar.addEventListener('click', function(e) {
        if (e.target.classList.contains('day')) {
            e.target.classList.toggle('selected');
            const selectedDates = Array.from(document.querySelectorAll('.day.selected')).map(el => el.getAttribute('data-date'));
            window.parent.postMessage({type: 'selected_dates', dates: selectedDates}, '*');
        }
    });
    </script>
    <style>
    #calendar table {
        border-collapse: collapse;
    }
    #calendar td {
        border: 1px solid #ddd;
        padding: 8px;
        cursor: pointer;
    }
    #calendar .selected {
        background-color: #4CAF50;
        color: white;
    }
    </style>
    """

    # Combine HTML and JavaScript
    full_html = f"{calendar_html}{js}"

    # Render the calendar
    components.html(full_html, height=300)

    # Handle the selected dates from JavaScript
    selected_dates = components.html(
        """
        <script>
        window.addEventListener('message', function(event) {
            if (event.data.type === 'selected_dates') {
                window.parent.postMessage({type: 'streamlit:setComponentValue', value: JSON.stringify(event.data.dates)}, '*');
            }
        });
        </script>
        """,
        height=0,
    )

    if selected_dates:
        try:
            st.session_state.selected_dates = set(json.loads(selected_dates))
        except json.JSONDecodeError:
            st.error("Error decoding selected dates")

    # Display selected dates
    st.write("Selected Dates:")
    for date in sorted(st.session_state.selected_dates):
        st.write(date)

if __name__ == "__main__":
    main()