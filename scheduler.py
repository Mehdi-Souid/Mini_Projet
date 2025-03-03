from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Dict, Set
import pandas as pd
from collections import defaultdict

@dataclass
class Teacher:
    name: str
    supervised_pfe_count: int = 0
    required_participation_count: int = 0
    current_participation_count: int = 0
    availability: List[datetime] = None

@dataclass
class PFE:
    topic: str
    student_name: str
    supervisor_name: str
    scheduled_time: datetime = None
    jury: Dict[str, str] = None  # role -> teacher_name

class PFEScheduler:
    def __init__(self):
        self.teachers: Dict[str, Teacher] = {}
        self.pfes: List[PFE] = []
        self.schedule: Dict[datetime, PFE] = {}
        
    def import_from_excel(self, file_path: str) -> None:
        """Import PFE data from Excel file"""
        df = pd.read_excel(file_path)
        for _, row in df.iterrows():
            pfe = PFE(
                topic=row['Topic'],
                student_name=row['Student Name'],
                supervisor_name=row['Supervisor Name']
            )
            self.pfes.append(pfe)
            
            # Update teacher supervision counts
            if pfe.supervisor_name not in self.teachers:
                self.teachers[pfe.supervisor_name] = Teacher(pfe.supervisor_name)
            self.teachers[pfe.supervisor_name].supervised_pfe_count += 1

        # Calculate required participation for each teacher
        for teacher in self.teachers.values():
            teacher.required_participation_count = teacher.supervised_pfe_count * 3

    def assign_juries(self) -> None:
        """Assign jury members to PFEs based on rules"""
        available_teachers = set(self.teachers.keys())
        
        for pfe in self.pfes:
            jury = {'supervisor': pfe.supervisor_name}
            
            # Find president and rapporteur
            potential_members = available_teachers - {pfe.supervisor_name}
            
            for role in ['president', 'rapporteur']:
                # Sort teachers by participation count (ascending)
                sorted_teachers = sorted(
                    potential_members,
                    key=lambda t: self.teachers[t].current_participation_count
                )
                
                for teacher_name in sorted_teachers:
                    teacher = self.teachers[teacher_name]
                    if teacher.current_participation_count < teacher.required_participation_count:
                        jury[role] = teacher_name
                        teacher.current_participation_count += 1
                        potential_members.remove(teacher_name)
                        break
            
            pfe.jury = jury

    def schedule_presentations(self, start_date: datetime, end_date: datetime, 
                            presentation_duration: timedelta = timedelta(minutes=60)) -> None:
        """Schedule PFE presentations based on constraints"""
        current_time = start_date
        scheduled_pfes = set()
        
        while current_time < end_date and len(scheduled_pfes) < len(self.pfes):
            for pfe in self.pfes:
                if pfe in scheduled_pfes:
                    continue
                    
                # Check if all jury members are available
                jury_available = all(
                    self.is_teacher_available(teacher_name, current_time)
                    for teacher_name in pfe.jury.values()
                )
                
                if jury_available:
                    pfe.scheduled_time = current_time
                    self.schedule[current_time] = pfe
                    scheduled_pfes.add(pfe)
                    
            current_time += presentation_duration

    def is_teacher_available(self, teacher_name: str, time: datetime) -> bool:
        """Check if a teacher is available at a given time"""
        teacher = self.teachers[teacher_name]
        if not teacher.availability:
            return True  # Assume always available if no specific availability set
            
        return any(
            start <= time <= end 
            for start, end in teacher.availability
        )

    def export_schedule_to_excel(self, output_path: str) -> None:
        """Export the final schedule to Excel"""
        data = []
        for time, pfe in sorted(self.schedule.items()):
            data.append({
                'Date': time.strftime('%Y-%m-%d'),
                'Time': time.strftime('%H:%M'),
                'Topic': pfe.topic,
                'Student': pfe.student_name,
                'Supervisor': pfe.jury['supervisor'],
                'President': pfe.jury['president'],
                'Rapporteur': pfe.jury['rapporteur']
            })
            
        df = pd.DataFrame(data)
        df.to_excel(output_path, index=False)

    def validate_schedule(self) -> List[str]:
        """Validate the schedule against all constraints"""
        errors = []
        teacher_presentations = defaultdict(list)
        
        for time, pfe in self.schedule.items():
            # Check for overlapping presentations
            for teacher_name in pfe.jury.values():
                teacher_times = teacher_presentations[teacher_name]
                for other_time in teacher_times:
                    if abs((time - other_time).total_seconds()) < 3600:  # 1 hour
                        errors.append(
                            f"Teacher {teacher_name} has overlapping presentations "
                            f"at {time} and {other_time}"
                        )
                teacher_times.append(time)
        
        # Validate participation counts
        for teacher_name, teacher in self.teachers.items():
            if teacher.current_participation_count < teacher.required_participation_count:
                errors.append(
                    f"Teacher {teacher_name} needs {teacher.required_participation_count} "
                    f"participations but only has {teacher.current_participation_count}"
                )
                
        return errors