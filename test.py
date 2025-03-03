import json
from datetime import datetime, timedelta
import random
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

class PFEScheduler:
    def __init__(self):
        self.presentations = []
        self.teachers = {}
        self.time_slots = []
        
    def add_presentation(self, topic, student, supervisor):
        self.presentations.append({
            'topic': topic,
            'student': student,
            'supervisor': supervisor,
            'scheduled_time': None,
            'jury': []
        })
        
        if supervisor not in self.teachers:
            self.teachers[supervisor] = {
                'supervised_count': 0,
                'jury_count': 0,
                'availability': []
            }
        self.teachers[supervisor]['supervised_count'] += 1
    
    def generate_time_slots(self, start_date, days, slots_per_day):
        current_date = datetime.strptime(start_date, '%Y-%m-%d')
        for _ in range(days):
            for hour in range(9, 9 + slots_per_day):
                self.time_slots.append(
                    current_date.replace(hour=hour, minute=0)
                )
            current_date += timedelta(days=1)
    
    def assign_jury(self, presentation):
        available_teachers = [
            t for t in self.teachers.keys()
            if t != presentation['supervisor']
        ]
        
        if len(available_teachers) < 2:
            raise ValueError("Not enough teachers for jury assignment")
            
        jury_members = random.sample(available_teachers, 2)
        presentation['jury'] = [
            {'role': 'President', 'name': jury_members[0]},
            {'role': 'Rapporteur', 'name': jury_members[1]},
            {'role': 'Supervisor', 'name': presentation['supervisor']}
        ]
        
        for member in jury_members:
            self.teachers[member]['jury_count'] += 1
    
    def schedule_presentations(self):
        self.presentations.sort(key=lambda x: x['supervisor'])
        
        for presentation in self.presentations:
            for slot in self.time_slots:
                self.assign_jury(presentation)
                jury_members = [m['name'] for m in presentation['jury']]
                
                slot_available = True
                for member in jury_members:
                    if slot in self.teachers[member].get('scheduled_slots', []):
                        slot_available = False
                        break
                
                if slot_available:
                    presentation['scheduled_time'] = slot
                    for member in jury_members:
                        if 'scheduled_slots' not in self.teachers[member]:
                            self.teachers[member]['scheduled_slots'] = []
                        self.teachers[member]['scheduled_slots'].append(slot)
                    break
    
    def export_schedule(self):
        schedule = []
        for p in sorted(self.presentations, key=lambda x: x['scheduled_time']):
            if p['scheduled_time']:
                schedule.append({
                    'date': p['scheduled_time'].strftime('%Y-%m-%d %H:%M'),
                    'topic': p['topic'],
                    'student': p['student'],
                    'jury': p['jury']
                })
        return schedule

    def generate_pdf(self, filename="schedule.pdf"):
        doc = SimpleDocTemplate(
            filename,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        # Get styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=1  # Center alignment
        )
        
        # Create story (content) for the PDF
        story = []
        
        # Add title
        title = Paragraph("PFE Presentation Schedule", title_style)
        story.append(title)
        story.append(Spacer(1, 20))
        
        # Prepare table data
        schedule = self.export_schedule()
        table_data = [
            ['Date & Time', 'Topic', 'Student', 'President', 'Rapporteur', 'Supervisor']
        ]
        
        for presentation in schedule:
            jury_dict = {j['role']: j['name'] for j in presentation['jury']}
            row = [
                presentation['date'],
                presentation['topic'],
                presentation['student'],
                jury_dict['President'],
                jury_dict['Rapporteur'],
                jury_dict['Supervisor']
            ]
            table_data.append(row)
        
        # Create table
        table = Table(table_data, colWidths=[1.2*inch, 2*inch, 1.5*inch, 1.2*inch, 1.2*inch, 1.2*inch])
        
        # Style the table
        table.setStyle(TableStyle([
            # Header style
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            # Cell style
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            # Row style
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            # Cell padding
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        story.append(table)
        
        # Add summary
        story.append(Spacer(1, 30))
        summary_style = ParagraphStyle(
            'Summary',
            parent=styles['Normal'],
            fontSize=12,
            spaceAfter=12
        )
        summary = Paragraph(f"Total Presentations: {len(schedule)}", summary_style)
        story.append(summary)
        
        # Build PDF
        doc.build(story)

# Example usage
if __name__ == "__main__":
    scheduler = PFEScheduler()
    
    # Add sample presentations
    presentations = [
        ("AI in Healthcare", "John Doe", "Dr. Smith"),
        ("Blockchain Security", "Jane Smith", "Dr. Johnson"),
        ("IoT Networks", "Bob Wilson", "Dr. Brown"),
        ("Machine Learning Applications", "Alice Johnson", "Dr. Smith"),
        ("Cloud Computing", "Charlie Brown", "Dr. Johnson"),
        ("Data Mining", "Eve Anderson", "Dr. Brown")
    ]
    
    for topic, student, supervisor in presentations:
        scheduler.add_presentation(topic, student, supervisor)
    
    # Generate time slots for 2 days, 4 slots per day
    scheduler.generate_time_slots('2024-03-20', 2, 4)
    
    # Schedule presentations
    scheduler.schedule_presentations()
    
    # Generate PDF schedule
    scheduler.generate_pdf("pfe_schedule.pdf")