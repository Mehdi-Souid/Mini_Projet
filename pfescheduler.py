from datetime import datetime, timedelta
import random
from collections import defaultdict
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import KeepTogether, Image
import qrcode
import io

def generate_qr_code(data):
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    return img_byte_arr

# Placeholder classifier - Needs to be replaced with actual classifier
class Classifier:
    def classify_project(self, topic):
        # Replace this with actual classification logic
        departments = ["Informatique", "Electrique", "Mecanique", "Civil", "Industriel"]
        return random.choice(departments)

classifier = Classifier()

class PFEScheduler:
    def __init__(self):
        self.presentations = []
        self.professors = {}  # Changed from teachers to professors for clarity
        self.time_slots = []
        self.unavailable_slots = {}
        self.rooms = self._initialize_rooms()
        self.room_schedule = {}  # Track room usage
        self.department_blocks = {
            "Informatique": "K",
            "Electrique": "I",
            "Mecanique": "M",
            "Civil": "G",
            "Industriel": "G"
        }
        # Track which professors are scheduled at which time slots
        self.professor_time_schedule = defaultdict(set)

    def _initialize_rooms(self):
        blocks = ['I', 'K', 'M', 'G']
        rooms = []
        for block in blocks:
            for room in range(1, 22):  # Rooms from 1 to 21
                room_id = f"{block}{room:02d}"
                rooms.append(room_id)
        return rooms

    def add_presentation(self, topic, student, supervisor):
        # Classify the project
        department = classifier.classify_project(topic)

        self.presentations.append({
            'topic': topic,
            'student': student,
            'supervisor': supervisor,
            'scheduled_time': None,
            'room': None,
            'jury': [],
            'department': department
        })

        if supervisor not in self.professors:
            self.professors[supervisor] = {
                'supervised_count': 0,
                'president_count': 0,
                'rapporteur_count': 0,
                'scheduled_slots': [],
                'scheduled_days': set()
            }
        self.professors[supervisor]['supervised_count'] += 1

    def set_professor_unavailability(self, professor, unavailable_slots):
        if professor not in self.unavailable_slots:
            self.unavailable_slots[professor] = []
        self.unavailable_slots[professor].extend(unavailable_slots)

    def is_professor_available(self, professor, time_slot):
        # Check if professor is explicitly marked as unavailable
        if time_slot in self.unavailable_slots.get(professor, []):
            return False
        
        # Check if professor is already scheduled for another presentation at this time
        if time_slot in self.professor_time_schedule.get(professor, set()):
            return False
            
        return True

    def generate_time_slots(self, start_date, days, slots_per_day):
        current_date = datetime.strptime(start_date, '%Y-%m-%d')
        for _ in range(days):
            for hour in range(9, 9 + slots_per_day):
                self.time_slots.append(
                    current_date.replace(hour=hour, minute=0)
                )
            current_date += timedelta(days=1)

    def get_available_room(self, time_slot, department):
        used_rooms = self.room_schedule.get(time_slot, set())
        
        # Get the block for this department
        block = self.department_blocks.get(department, "K")  # Default to K if department not found
        
        # Filter rooms by department block
        department_rooms = [r for r in self.rooms if r.startswith(block) and r not in used_rooms]
        
        if not department_rooms:
            # If no rooms available in the preferred block, try any available room
            available_rooms = [r for r in self.rooms if r not in used_rooms]
            if not available_rooms:
                raise ValueError(f"No rooms available for this time slot ({time_slot})")
            return random.choice(available_rooms)
        
        return random.choice(department_rooms)

    def calculate_professor_requirements(self):
        """Calculate how many times each professor should serve in each role"""
        for professor in self.professors:
            supervised = self.professors[professor]['supervised_count']
            # Each professor should participate in 3 * supervised presentations
            # Once as supervisor (already counted), once as president, once as rapporteur
            self.professors[professor]['president_target'] = supervised
            self.professors[professor]['rapporteur_target'] = supervised

    def get_best_jury_members(self, presentation, time_slot):
        """Select jury members based on balanced participation and scheduling constraints"""
        supervisor = presentation['supervisor']
        department = presentation['department']
        
        # Get professors from the same department (excluding the supervisor)
        department_professors = [
            p for p in self.professors.keys() 
            if p != supervisor and self.is_professor_available(p, time_slot)
            and time_slot not in self.professors[p]['scheduled_slots']
        ]
        
        if len(department_professors) < 2:
            # Not enough professors available
            return None
        
        # Sort professors by how far they are from their targets
        president_candidates = sorted(
            department_professors,
            key=lambda p: (
                # Prioritize professors who need to be president more
                self.professors[p]['president_target'] - self.professors[p]['president_count'],
                # Then prioritize professors who are already scheduled on this day
                -1 if time_slot.date() in self.professors[p]['scheduled_days'] else 0,
                # Then prioritize professors with fewer total assignments
                -(self.professors[p]['president_count'] + self.professors[p]['rapporteur_count'])
            ),
            reverse=True
        )
        
        if not president_candidates:
            return None
            
        president = president_candidates[0]
        
        # Remove the selected president from candidates for rapporteur
        rapporteur_candidates = [p for p in department_professors if p != president]
        
        if not rapporteur_candidates:
            return None
            
        rapporteur_candidates = sorted(
            rapporteur_candidates,
            key=lambda p: (
                # Prioritize professors who need to be rapporteur more
                self.professors[p]['rapporteur_target'] - self.professors[p]['rapporteur_count'],
                # Then prioritize professors who are already scheduled on this day
                -1 if time_slot.date() in self.professors[p]['scheduled_days'] else 0,
                # Then prioritize professors with fewer total assignments
                -(self.professors[p]['president_count'] + self.professors[p]['rapporteur_count'])
            ),
            reverse=True
        )
        
        rapporteur = rapporteur_candidates[0]
        
        return {
            'president': president,
            'rapporteur': rapporteur
        }

    def assign_jury(self, presentation, time_slot):
        jury_selection = self.get_best_jury_members(presentation, time_slot)
        
        if not jury_selection:
            return False
            
        president = jury_selection['president']
        rapporteur = jury_selection['rapporteur']
        supervisor = presentation['supervisor']
        
        # Double-check that all jury members are available at this time
        # This is a safety check in case availability changed since get_best_jury_members was called
        if not (self.is_professor_available(president, time_slot) and 
                self.is_professor_available(rapporteur, time_slot) and
                self.is_professor_available(supervisor, time_slot)):
            return False
        
        presentation['jury'] = [
            {'role': 'President', 'name': president},
            {'role': 'Rapporteur', 'name': rapporteur},
            {'role': 'Supervisor', 'name': supervisor}
        ]
        
        # Update counts
        self.professors[president]['president_count'] += 1
        self.professors[rapporteur]['rapporteur_count'] += 1
        
        # Mark all jury members as scheduled for this time slot
        self.professor_time_schedule[president].add(time_slot)
        self.professor_time_schedule[rapporteur].add(time_slot)
        self.professor_time_schedule[supervisor].add(time_slot)
        
        return True

    def group_by_supervisor(self):
        """Group presentations by supervisor to schedule them together"""
        supervisor_groups = defaultdict(list)
        for presentation in self.presentations:
            supervisor_groups[presentation['supervisor']].append(presentation)
        return supervisor_groups

    def get_consecutive_days(self, start_date, num_days_needed):
        """Find consecutive available days starting from a given date"""
        all_dates = sorted(list(set(slot.date() for slot in self.time_slots)))
        
        if start_date not in all_dates:
            # If start_date is not in our available dates, find the closest one
            future_dates = [d for d in all_dates if d >= start_date]
            if not future_dates:
                return []
            start_date = future_dates[0]
        
        start_idx = all_dates.index(start_date)
        
        # Check if we have enough consecutive days from this starting point
        if start_idx + num_days_needed > len(all_dates):
            return []
            
        consecutive_days = []
        current_date = all_dates[start_idx]
        
        for i in range(num_days_needed):
            if i > 0:
                # Check if this date is consecutive to the previous one
                expected_date = consecutive_days[-1] + timedelta(days=1)
                if all_dates[start_idx + i] != expected_date:
                    return []  # Not consecutive
            
            consecutive_days.append(all_dates[start_idx + i])
            
        return consecutive_days

    def schedule_presentations(self):
        # First calculate how many times each professor should serve in each role
        self.calculate_professor_requirements()
        
        # Group presentations by supervisor
        supervisor_groups = self.group_by_supervisor()
        
        # Sort supervisors by number of students (descending)
        sorted_supervisors = sorted(
            supervisor_groups.keys(),
            key=lambda s: len(supervisor_groups[s]),
            reverse=True
        )
        
        unscheduled = []
        
        # First pass: try to schedule all presentations for each supervisor on consecutive days
        # and in consecutive time slots within each day
        for supervisor in sorted_supervisors:
            presentations = supervisor_groups[supervisor]
            
            # Calculate how many days we need for this supervisor
            # Assuming we can schedule at most 3 presentations per day (to keep them consecutive)
            presentations_per_day = 3
            days_needed = (len(presentations) + presentations_per_day - 1) // presentations_per_day
            
            # Get all available dates
            all_dates = sorted(list(set(slot.date() for slot in self.time_slots)))
            
            scheduled_all = False
            
            # Try to find consecutive days
            for start_date in all_dates:
                if scheduled_all:
                    break
                    
                consecutive_days = self.get_consecutive_days(start_date, days_needed)
                
                if not consecutive_days:
                    continue
                
                # Try to schedule presentations across these consecutive days
                presentations_scheduled = []
                presentations_by_day = {}
                
                # Distribute presentations across days
                for i, presentation in enumerate(presentations):
                    day_index = i // presentations_per_day
                    if day_index >= len(consecutive_days):
                        break
                        
                    day = consecutive_days[day_index]
                    
                    if day not in presentations_by_day:
                        presentations_by_day[day] = []
                    
                    presentations_by_day[day].append(presentation)
                
                # Now try to schedule each day's presentations in consecutive slots
                all_scheduled = True
                
                for day, day_presentations in presentations_by_day.items():
                    # Get slots for this day
                    day_slots = sorted([
                        slot for slot in self.time_slots 
                        if slot.date() == day
                    ], key=lambda x: x.hour)
                    
                    # Find consecutive available slots
                    consecutive_slots = []
                    current_consecutive = []
                    
                    for i, slot in enumerate(day_slots):
                        # Check if supervisor is available for this slot
                        if self.is_professor_available(supervisor, slot):
                            current_consecutive.append(slot)
                            
                            # If we're at the end of the day or the next slot is not consecutive
                            if i == len(day_slots) - 1 or day_slots[i+1].hour > slot.hour + 1:
                                if len(current_consecutive) >= len(day_presentations):
                                    consecutive_slots = current_consecutive[:len(day_presentations)]
                                    break
                                current_consecutive = []
                        else:
                            current_consecutive = []
                    
                    if len(consecutive_slots) < len(day_presentations):
                        all_scheduled = False
                        break
                    
                    # Schedule presentations in these consecutive slots
                    for i, presentation in enumerate(day_presentations):
                        slot = consecutive_slots[i]
                        
                        # Try to assign jury
                        if self.assign_jury(presentation, slot):
                            try:
                                room = self.get_available_room(slot, presentation['department'])
                                presentation['scheduled_time'] = slot
                                presentation['room'] = room
                                
                                # Update room schedule
                                if slot not in self.room_schedule:
                                    self.room_schedule[slot] = set()
                                self.room_schedule[slot].add(room)
                                
                                # Update professor schedules
                                for jury_member in presentation['jury']:
                                    prof_name = jury_member['name']
                                    self.professors[prof_name]['scheduled_slots'].append(slot)
                                    self.professors[prof_name]['scheduled_days'].add(slot.date())
                                
                                presentations_scheduled.append(presentation)
                            except ValueError:
                                # No room available, scheduling failed
                                all_scheduled = False
                                break
                        else:
                            # Couldn't assign jury, scheduling failed
                            all_scheduled = False
                            break
                
                if all_scheduled and len(presentations_scheduled) == len(presentations):
                    scheduled_all = True
            
            # If couldn't schedule all together, add to unscheduled for second pass
            if not scheduled_all:
                unscheduled.extend([p for p in presentations if not p.get('scheduled_time')])
        
        # Second pass: try to schedule remaining presentations with more flexibility
        still_unscheduled = []
        
        for presentation in unscheduled:
            if presentation.get('scheduled_time'):
                # Already scheduled in first pass
                continue
                
            supervisor = presentation['supervisor']
            scheduled = False
            
            # Prioritize days where the supervisor already has presentations
            supervisor_days = sorted(
                list(self.professors[supervisor]['scheduled_days']),
                key=lambda d: len([
                    p for p in self.presentations 
                    if p.get('scheduled_time') and p.get('scheduled_time').date() == d
                ]),
                reverse=True
            )
            
            # If supervisor already has scheduled days, try to use consecutive days
            if supervisor_days:
                # Sort days chronologically
                supervisor_days.sort()
                
                # Try to find days adjacent to existing scheduled days
                all_dates = sorted(list(set(slot.date() for slot in self.time_slots)))
                
                adjacent_days = set()
                
                for day in supervisor_days:
                    # Try day before
                    day_before = day - timedelta(days=1)
                    if day_before in all_dates and day_before not in supervisor_days:
                        adjacent_days.add(day_before)
                    
                    # Try day after
                    day_after = day + timedelta(days=1)
                    if day_after in all_dates and day_after not in supervisor_days:
                        adjacent_days.add(day_after)
                
                # Sort adjacent days by how close they are to existing days
                adjacent_days = sorted(adjacent_days, key=lambda d: min(abs((d - sd).days) for sd in supervisor_days))
                
                # Try adjacent days first
                for day in adjacent_days:
                    if scheduled:
                        break
                        
                    # Get slots for this day
                    day_slots = sorted([
                        slot for slot in self.time_slots 
                        if slot.date() == day and self.is_professor_available(supervisor, slot)
                    ], key=lambda x: x.hour)
                    
                    for slot in day_slots:
                        if self.assign_jury(presentation, slot):
                            try:
                                room = self.get_available_room(slot, presentation['department'])
                                presentation['scheduled_time'] = slot
                                presentation['room'] = room
                                
                                # Update room schedule
                                if slot not in self.room_schedule:
                                    self.room_schedule[slot] = set()
                                self.room_schedule[slot].add(room)
                                
                                # Update professor schedules
                                for jury_member in presentation['jury']:
                                    prof_name = jury_member['name']
                                    self.professors[prof_name]['scheduled_slots'].append(slot)
                                    self.professors[prof_name]['scheduled_days'].add(slot.date())
                                
                                scheduled = True
                                break
                            except ValueError:
                                continue
            
            # If still not scheduled, try supervisor's existing days
            if not scheduled and supervisor_days:
                for day in supervisor_days:
                    if scheduled:
                        break
                        
                    # Get all slots for this day
                    day_slots = [slot for slot in self.time_slots if slot.date() == day]
                    
                    # Sort slots by hour to prioritize consecutive scheduling
                    day_slots.sort(key=lambda x: x.hour)
                    
                    # Find slots where the supervisor already has presentations
                    supervisor_slots = [
                        slot for slot in self.professors[supervisor]['scheduled_slots']
                        if slot.date() == day
                    ]
                    
                    # Sort supervisor's existing slots by hour
                    supervisor_slots.sort(key=lambda x: x.hour)
                    
                    # Try to find slots adjacent to existing ones
                    adjacent_slots = []
                    
                    for existing_slot in supervisor_slots:
                        # Try slot before
                        before_slot = datetime(
                            existing_slot.year, existing_slot.month, existing_slot.day,
                            existing_slot.hour - 1, existing_slot.minute
                        )
                        if before_slot in day_slots and before_slot not in self.professors[supervisor]['scheduled_slots']:
                            adjacent_slots.append(before_slot)
                        
                        # Try slot after
                        after_slot = datetime(
                            existing_slot.year, existing_slot.month, existing_slot.day,
                            existing_slot.hour + 1, existing_slot.minute
                        )
                        if after_slot in day_slots and after_slot not in self.professors[supervisor]['scheduled_slots']:
                            adjacent_slots.append(after_slot)
                    
                    # Try adjacent slots first
                    for slot in adjacent_slots:
                        if self.is_professor_available(supervisor, slot):
                            if self.assign_jury(presentation, slot):
                                try:
                                    room = self.get_available_room(slot, presentation['department'])
                                    presentation['scheduled_time'] = slot
                                    presentation['room'] = room
                                    
                                    # Update room schedule
                                    if slot not in self.room_schedule:
                                        self.room_schedule[slot] = set()
                                    self.room_schedule[slot].add(room)
                                    
                                    # Update professor schedules
                                    for jury_member in presentation['jury']:
                                        prof_name = jury_member['name']
                                        self.professors[prof_name]['scheduled_slots'].append(slot)
                                        self.professors[prof_name]['scheduled_days'].add(slot.date())
                                    
                                    scheduled = True
                                    break
                                except ValueError:
                                    continue
                    
                    # If not scheduled with adjacent slots, try any available slot on this day
                    if not scheduled:
                        for slot in day_slots:
                            if slot not in self.professors[supervisor]['scheduled_slots'] and self.is_professor_available(supervisor, slot):
                                if self.assign_jury(presentation, slot):
                                    try:
                                        room = self.get_available_room(slot, presentation['department'])
                                        presentation['scheduled_time'] = slot
                                        presentation['room'] = room
                                        
                                        # Update room schedule
                                        if slot not in self.room_schedule:
                                            self.room_schedule[slot] = set()
                                        self.room_schedule[slot].add(room)
                                        
                                        # Update professor schedules
                                        for jury_member in presentation['jury']:
                                            prof_name = jury_member['name']
                                            self.professors[prof_name]['scheduled_slots'].append(slot)
                                            self.professors[prof_name]['scheduled_days'].add(slot.date())
                                        
                                        scheduled = True
                                        break
                                    except ValueError:
                                        continue
            
            # If still not scheduled, try any available slot on any day
            if not scheduled:
                # Group slots by day and sort them
                slots_by_day = defaultdict(list)
                for slot in self.time_slots:
                    if slot not in self.professors[supervisor]['scheduled_slots'] and self.is_professor_available(supervisor, slot):
                        slots_by_day[slot.date()].append(slot)
                
                for day, day_slots in slots_by_day.items():
                    if scheduled:
                        break
                    
                    # Sort slots by hour
                    day_slots.sort(key=lambda x: x.hour)
                    
                    for slot in day_slots:
                        if self.assign_jury(presentation, slot):
                            try:
                                room = self.get_available_room(slot, presentation['department'])
                                presentation['scheduled_time'] = slot
                                presentation['room'] = room
                                
                                # Update room schedule
                                if slot not in self.room_schedule:
                                    self.room_schedule[slot] = set()
                                self.room_schedule[slot].add(room)
                                
                                # Update professor schedules
                                for jury_member in presentation['jury']:
                                    prof_name = jury_member['name']
                                    self.professors[prof_name]['scheduled_slots'].append(slot)
                                    self.professors[prof_name]['scheduled_days'].add(slot.date())
                                
                                scheduled = True
                                break
                            except ValueError:
                                continue
            
            if not scheduled:
                still_unscheduled.append(presentation)
        
        if still_unscheduled:
            print(f"Warning: Could not schedule {len(still_unscheduled)} presentations due to constraints")
            for p in still_unscheduled:
                print(f"  - {p['student']}: {p['topic']} (Supervisor: {p['supervisor']})")

    def get_room_usage(self):
        room_usage = {room: [] for room in self.rooms}
        for presentation in self.presentations:
            if presentation['scheduled_time'] and presentation['room']:
                room_usage[presentation['room']].append({
                    'time': presentation['scheduled_time'],
                    'student': presentation['student']
                })
        return room_usage

    def get_professor_schedule(self):
        """Get a summary of each professor's schedule"""
        professor_schedule = {}
        
        for professor in self.professors:
            professor_schedule[professor] = {
                'supervised_count': self.professors[professor]['supervised_count'],
                'president_count': self.professors[professor]['president_count'],
                'rapporteur_count': self.professors[professor]['rapporteur_count'],
                'total_participations': (
                    self.professors[professor]['supervised_count'] +
                    self.professors[professor]['president_count'] +
                    self.professors[professor]['rapporteur_count']
                ),
                'scheduled_days': sorted(list(self.professors[professor]['scheduled_days'])),
                'presentations_by_day': defaultdict(list)
            }
        
        # Add presentations to each professor's schedule
        for presentation in self.presentations:
            if not presentation['scheduled_time']:
                continue
                
            day = presentation['scheduled_time'].date()
            
            # Add to supervisor's schedule
            supervisor = presentation['supervisor']
            professor_schedule[supervisor]['presentations_by_day'][day].append({
                'time': presentation['scheduled_time'],
                'role': 'Supervisor',
                'student': presentation['student'],
                'room': presentation['room']
            })
            
            # Add to jury members' schedules
            for jury_member in presentation['jury']:
                if jury_member['role'] == 'Supervisor':
                    continue  # Already added above
                    
                professor = jury_member['name']
                professor_schedule[professor]['presentations_by_day'][day].append({
                    'time': presentation['scheduled_time'],
                    'role': jury_member['role'],
                    'student': presentation['student'],
                    'room': presentation['room']
                })
        
        return professor_schedule

    def export_schedule(self):
        schedule = []
        for p in sorted(self.presentations, key=lambda x: (x['scheduled_time'] if x['scheduled_time'] else datetime.max)):
            if p['scheduled_time']:
                schedule.append({
                    'date': p['scheduled_time'].strftime('%Y-%m-%d %H:%M'),
                    'topic': p['topic'],
                    'student': p['student'],
                    'room': p['room'],
                    'jury': p['jury'],
                    'department': p['department']
                })
        return schedule

    def generate_pdf(self, filename="schedule.pdf"):
        from reportlab.lib.units import cm, mm

        # Custom large page size (A2 landscape)
        page_size = landscape((594*mm, 420*mm))  # A2 dimensions

        doc = SimpleDocTemplate(
            filename,
            pagesize=page_size,
            rightMargin=1*cm,
            leftMargin=1*cm,
            topMargin=1*cm,
            bottomMargin=1*cm
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=36,
            spaceAfter=40,
            alignment=1
        )

        story = []

        title = Paragraph("Planning des Soutenances PFE", title_style)
        story.append(title)
        story.append(Spacer(1, 30))

        schedule = self.export_schedule()

        # Create paragraph styles for table cells
        cell_style = ParagraphStyle(
            'CellStyle',
            parent=styles['Normal'],
            fontSize=14,
            leading=16,
            alignment=1,  # Center alignment
        )

        header_style = ParagraphStyle(
            'HeaderStyle',
            parent=cell_style,
            fontSize=16,
            leading=18,
            fontName='Helvetica-Bold',
        )

        table_data = [
            [Paragraph(header, header_style) for header in [
                'Date & Time', 'Department', 'Topic', 'Student', 'Room',
                'President', 'Rapporteur', 'Supervisor'
            ]]
        ]

        for presentation in schedule:
            jury_dict = {j['role']: j['name'] for j in presentation['jury']}
            row = [
                Paragraph(presentation['date'], cell_style),
                Paragraph(presentation['department'], cell_style),
                Paragraph(presentation['topic'], cell_style),
                Paragraph(presentation['student'], cell_style),
                Paragraph(presentation['room'], cell_style),
                Paragraph(jury_dict['President'], cell_style),
                Paragraph(jury_dict['Rapporteur'], cell_style),
                Paragraph(jury_dict['Supervisor'], cell_style)
            ]
            table_data.append(row)

        # Calculate column widths based on A2 landscape size
        available_width = page_size[0] - 2*cm  # Total width minus margins
        col_widths = [
            available_width * 0.10,  # Date & Time
            available_width * 0.12,  # Department
            available_width * 0.20,  # Topic
            available_width * 0.12,  # Student
            available_width * 0.08,  # Room
            available_width * 0.10,  # President
            available_width * 0.10,  # Rapporteur
            available_width * 0.18   # Supervisor
        ]

        table = Table(table_data, colWidths=col_widths, repeatRows=1)

        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))

        # Wrap the table in a KeepTogether to prevent it from breaking across pages
        story.append(KeepTogether(table))

        story.append(Spacer(1, 40))
        summary_style = ParagraphStyle(
            'Summary',
            parent=styles['Normal'],
            fontSize=18,
            spaceAfter=16
        )
        summary = Paragraph(f"Total Presentations: {len(schedule)}", summary_style)
        story.append(summary)

        # Add professor participation summary
        story.append(Spacer(1, 20))
        professor_summary_title = Paragraph("Professor Participation Summary", summary_style)
        story.append(professor_summary_title)
        story.append(Spacer(1, 10))

        professor_data = [
            [Paragraph(header, header_style) for header in [
                'Professor', 'As Supervisor', 'As President', 'As Rapporteur', 'Total', 'Days Scheduled'
            ]]
        ]

        for professor, stats in self.get_professor_schedule().items():
            days_str = ", ".join([d.strftime('%Y-%m-%d') for d in stats['scheduled_days']])
            row = [
                Paragraph(professor, cell_style),
                Paragraph(str(stats['supervised_count']), cell_style),
                Paragraph(str(stats['president_count']), cell_style),
                Paragraph(str(stats['rapporteur_count']), cell_style),
                Paragraph(str(stats['total_participations']), cell_style),
                Paragraph(days_str, cell_style),
            ]
            professor_data.append(row)

        # Calculate column widths for professor table
        prof_col_widths = [
            available_width * 0.20,  # Professor
            available_width * 0.10,  # As Supervisor
            available_width * 0.10,  # As President
            available_width * 0.10,  # As Rapporteur
            available_width * 0.10,  # Total
            available_width * 0.40,  # Days Scheduled
        ]

        professor_table = Table(professor_data, colWidths=prof_col_widths, repeatRows=1)
        professor_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))

        story.append(KeepTogether(professor_table))

        doc.build(story)

    def generate_professor_schedules_pdf(self, filename="professor_schedules.pdf"):
        """Generate individual schedules for each professor"""
        from reportlab.lib.units import cm, mm

        # Use A4 landscape for individual schedules
        page_size = landscape((297*mm, 210*mm))

        doc = SimpleDocTemplate(
            filename,
            pagesize=page_size,
            rightMargin=1*cm,
            leftMargin=1*cm,
            topMargin=1*cm,
            bottomMargin=1*cm
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=20,
            alignment=1
        )
        
        subtitle_style = ParagraphStyle(
            'Subtitle',
            parent=styles['Heading2'],
            fontSize=18,
            spaceAfter=10,
            alignment=1
        )

        cell_style = ParagraphStyle(
            'CellStyle',
            parent=styles['Normal'],
            fontSize=12,
            leading=14,
            alignment=1,
        )

        header_style = ParagraphStyle(
            'HeaderStyle',
            parent=cell_style,
            fontSize=14,
            leading=16,
            fontName='Helvetica-Bold',
        )

        story = []
        
        # Main title
        title = Paragraph("PFE Schedules by Professor", title_style)
        story.append(title)
        story.append(Spacer(1, 20))
        
        # Get professor schedules
        professor_schedules = self.get_professor_schedule()
        
        # Sort professors by name
        for professor_name in sorted(professor_schedules.keys()):
            professor_data = professor_schedules[professor_name]
            
            # Professor name as subtitle
            prof_title = Paragraph(f"Schedule for: {professor_name}", subtitle_style)
            story.append(prof_title)
            
            # Summary of participation
            summary = Paragraph(
                f"Supervising: {professor_data['supervised_count']} | " +
                f"As President: {professor_data['president_count']} | " +
                f"As Rapporteur: {professor_data['rapporteur_count']} | " +
                f"Total: {professor_data['total_participations']}",
                cell_style
            )
            story.append(summary)
            story.append(Spacer(1, 10))
            
            # Create a table for each day the professor has presentations
            for day in sorted(professor_data['presentations_by_day'].keys()):
                day_presentations = professor_data['presentations_by_day'][day]
                
                # Sort presentations by time
                day_presentations.sort(key=lambda x: x['time'])
                
                # Day header
                day_header = Paragraph(f"Day: {day.strftime('%Y-%m-%d')}", header_style)
                story.append(day_header)
                story.append(Spacer(1, 5))
                
                # Table for this day's presentations
                table_data = [
                    [Paragraph(header, header_style) for header in [
                        'Time', 'Student', 'Room', 'Role'
                    ]]
                ]
                
                for presentation in day_presentations:
                    row = [
                        Paragraph(presentation['time'].strftime('%H:%M'), cell_style),
                        Paragraph(presentation['student'], cell_style),
                        Paragraph(presentation['room'], cell_style),
                        Paragraph(presentation['role'], cell_style)
                    ]
                    table_data.append(row)
                
                # Calculate column widths
                available_width = page_size[0] - 2*cm
                col_widths = [
                    available_width * 0.15,  # Time
                    available_width * 0.40,  # Student
                    available_width * 0.15,  # Room
                    available_width * 0.30   # Role
                ]
                
                table = Table(table_data, colWidths=col_widths, repeatRows=1)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
                    ('TOPPADDING', (0, 0), (-1, -1), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                    ('LEFTPADDING', (0, 0), (-1, -1), 6),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ]))
                
                story.append(table)
                story.append(Spacer(1, 15))
            
            # Add a page break after each professor (except the last one)
            story.append(Spacer(1, 20))
            story.append(Paragraph("", styles['Normal']))
            story.append(Spacer(1, 20))
        
        doc.build(story)