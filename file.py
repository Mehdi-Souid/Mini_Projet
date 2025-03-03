import pandas as pd
import random
from datetime import datetime, timedelta

# Sample data
topics = [
    "Development of an AI-powered Student Attendance System",
    "Blockchain-based Academic Certificate Verification Platform",
    "Smart Campus Navigation System using IoT",
    "Machine Learning for Predictive Maintenance in Industrial Systems",
    "Cloud-based Laboratory Resource Management System",
    "Autonomous Drone for Campus Security",
    "Virtual Reality Training Platform for Engineering Students",
    "Smart Energy Management System for University Buildings",
    "Mobile App for Student Mental Health Support",
    "Automated Parking Management System using Computer Vision",
    "Real-time Public Transportation Tracking System",
    "Waste Management Optimization using IoT Sensors",
    "E-learning Platform with AI-powered Student Analytics",
    "Biometric Authentication System for Exam Halls",
    "Smart Library Management System with RFID Integration"
]

teachers = [
    "Dr. Sarah Chen",
    "Prof. Michael Rodriguez",
    "Dr. Emma Thompson",
    "Prof. Ahmed Hassan",
    "Dr. Marie Dubois",
    "Prof. James Wilson",
    "Dr. Sofia Garcia",
    "Prof. Yuki Tanaka"
]

student_first_names = [
    "Adam", "Sophia", "Mohamed", "Emma", "Lucas", "Olivia", 
    "Liam", "Ava", "Noah", "Isabella", "Ethan", "Mia", 
    "Oliver", "Charlotte", "Amir"
]

student_last_names = [
    "Smith", "Johnson", "Brown", "Davis", "Miller", "Wilson",
    "Moore", "Taylor", "Anderson", "Thomas", "Jackson", "White",
    "Harris", "Martin", "Thompson"
]

# Generate sample data
data = []
used_topics = set()
used_students = set()

for _ in range(15):  # Generate 15 PFE projects
    # Select unique topic
    topic = random.choice([t for t in topics if t not in used_topics])
    used_topics.add(topic)
    
    # Generate unique student name
    while True:
        student_name = f"{random.choice(student_first_names)} {random.choice(student_last_names)}"
        if student_name not in used_students:
            used_students.add(student_name)
            break
    
    # Assign supervisor
    supervisor = random.choice(teachers)
    
    data.append({
        "Topic": topic,
        "Student Name": student_name,
        "Supervisor Name": supervisor
    })

# Create DataFrame
df = pd.DataFrame(data)

# Save to Excel
df.to_excel("pfe_sample_data.xlsx", index=False)

# Display the first few rows
print("Sample PFE Data Generated:")
print(df.head())
print(f"\nTotal PFE projects: {len(df)}")
print(f"Total supervisors: {len(set(df['Supervisor Name']))}")

# Generate teacher availability data
availability_data = []
start_date = datetime(2024, 6, 1, 9, 0)  # June 1st, 2024 at 9 AM

for teacher in teachers:
    # Generate 5 random available time slots for each teacher
    for _ in range(5):
        day_offset = random.randint(0, 13)  # 2 weeks period
        hour_offset = random.randint(0, 7)  # 9 AM to 4 PM
        
        start_time = start_date + timedelta(days=day_offset, hours=hour_offset)
        end_time = start_time + timedelta(hours=4)  # 4-hour availability blocks
        
        availability_data.append({
            "Teacher Name": teacher,
            "Start Time": start_time,
            "End Time": end_time
        })

# Create availability DataFrame
availability_df = pd.DataFrame(availability_data)

# Save teacher availability to a separate sheet
with pd.ExcelWriter("pfe_sample_data.xlsx", engine='openpyxl', mode='a') as writer:
    availability_df.to_excel(writer, sheet_name='Teacher Availability', index=False)

print("\nTeacher Availability Data:")
print(availability_df.head())