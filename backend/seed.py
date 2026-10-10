"""Seed script generating realistic hackathon demo data with 7 distinct pattern cases."""
import random
from datetime import date, timedelta
from sqlalchemy.orm import Session

from app.database import engine, Base, SessionLocal
from app.models.models import (
    User, Mentor, Teacher, ClassRoom, Student, Subject, TeacherClassSubject,
    Attendance, AttendanceStatus, Role, RiskLevel, Exam
)
from app.security import hash_password
from app.services.analytics import run_analytics_for_student
from app.services.counselling import create_or_get_counselling_case



def seed_database():
    print("[SEED] Resetting database tables...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()

    # 1. Create Mentor
    mentor_user = User(
        role=Role.mentor,
        name="Alex Morgan",
        email="mentor@example.com",
        password_hash=hash_password("password123"),
        is_active=True
    )
    db.add(mentor_user)
    db.commit()
    db.refresh(mentor_user)

    mentor = Mentor(user_id=mentor_user.id, department="Computer Science & Engineering")
    db.add(mentor)
    db.commit()
    db.refresh(mentor)

    # 2. Create 3 Teachers
    teachers = []
    teacher_names = [("Dr. Sarah Jenkins", "teacher1@example.com"),
                     ("Prof. David Miller", "teacher2@example.com"),
                     ("Dr. Emily Watson", "teacher3@example.com")]
    for name, email in teacher_names:
        u = User(
            role=Role.teacher,
            name=name,
            email=email,
            password_hash=hash_password("password123"),
            is_active=True
        )
        db.add(u)
        db.commit()
        db.refresh(u)
        t = Teacher(user_id=u.id, department="CSE")
        db.add(t)
        db.commit()
        db.refresh(t)
        teachers.append(t)

    # 3. Create Class
    classroom = ClassRoom(
        mentor_id=mentor.id,
        name="6th Sem CSE - Section A",
        branch="Computer Science",
        semester=6,
        section="A",
        academic_year="2026-27"
    )
    db.add(classroom)
    db.commit()
    db.refresh(classroom)

    # 4. Create 5 Subjects
    subject_data = [
        ("Database Management Systems", "CS601"),
        ("Machine Learning", "CS602"),
        ("Computer Networks", "CS603"),
        ("Web Technologies", "CS604"),
        ("Software Engineering", "CS605")
    ]
    subjects = []
    for name, code in subject_data:
        sub = Subject(class_id=classroom.id, name=name, code=code)
        db.add(sub)
        db.commit()
        db.refresh(sub)
        subjects.append(sub)

    # Map teachers to subjects
    for i, sub in enumerate(subjects):
        t = teachers[i % len(teachers)]
        tcs = TeacherClassSubject(
            teacher_id=t.id,
            class_id=classroom.id,
            subject_id=sub.id,
            assigned_by_mentor=True
        )
        db.add(tcs)
    db.commit()

    # 5. Create ~30 Students
    student_specs = [
        ("Alice Smith (Sudden Drop)", "1VA21CS001", "alice@example.com", "parent.alice@example.com"),
        ("Bob Jones (Continuous Absence)", "1VA21CS002", "bob@example.com", "parent.bob@example.com"),
        ("Charlie Brown (Slow Decline)", "1VA21CS003", "charlie@example.com", "parent.charlie@example.com"),
        ("Diana Prince (Slow Improvement)", "1VA21CS004", "diana@example.com", "parent.diana@example.com"),
        ("Evan Wright (Subject Drop)", "1VA21CS005", "evan@example.com", "parent.evan@example.com"),
        ("Fiona Gallagher (Recovery)", "1VA21CS006", "fiona@example.com", "parent.fiona@example.com"),
        ("George Clark (Missing Records)", "1VA21CS007", "george@example.com", "parent.george@example.com"),
    ]

    # Add remaining students up to 30
    for i in range(8, 31):
        student_specs.append((f"Student {i:02d}", f"1VA21CS{i:03d}", f"student{i}@example.com", f"parent{i}@example.com"))

    students = []
    for idx, (name, usn, email, p_email) in enumerate(student_specs):
        user_email = f"sharmilashroff512+{usn.lower()}@gmail.com" if idx > 0 else "sharmilashroff512@gmail.com"
        u = User(
            role=Role.student,
            name=name,
            email=user_email,
            usn=usn,
            password_hash=hash_password(usn),
            is_active=True
        )
        db.add(u)
        db.commit()
        db.refresh(u)
        s = Student(
            user_id=u.id,
            class_id=classroom.id,
            name=name,
            usn=usn,
            email="sharmilashroff512@gmail.com",
            parent_email=p_email,
            parent_phone="9876543210"
        )
        db.add(s)
        db.commit()
        db.refresh(s)
        students.append(s)

    # 6. Generate 3 Months Attendance History (60 school days)
    start_date = date.today() - timedelta(days=75)
    days = [start_date + timedelta(days=i) for i in range(75) if (start_date + timedelta(days=i)).weekday() < 5]
    days = days[:60]  # 60 working days

    print(f"[SEED] Generating attendance over {len(days)} working days for 30 students across 5 subjects...")

    for day_idx, d in enumerate(days):
        for sub_idx, sub in enumerate(subjects):
            for s_idx, student in enumerate(students):

                # Default status: present
                status = AttendanceStatus.present

                # --- Case A: Alice Smith (Sudden Drop in DBMS) ---
                if s_idx == 0 and sub.code == "CS601":
                    if day_idx < 45:
                        status = AttendanceStatus.present if random.random() < 0.92 else AttendanceStatus.absent
                    else:
                        status = AttendanceStatus.absent if random.random() < 0.85 else AttendanceStatus.present

                # --- Case B: Bob Jones (Continuous Absence in ML) ---
                elif s_idx == 1 and sub.code == "CS602":
                    if day_idx >= 54:  # Last 6 consecutive classes absent
                        status = AttendanceStatus.absent
                    else:
                        status = AttendanceStatus.present if random.random() < 0.90 else AttendanceStatus.absent

                # --- Case C: Charlie Brown (Slow Decline in Web Tech) ---
                elif s_idx == 2 and sub.code == "CS604":
                    prob_present = max(0.40, 0.95 - (day_idx / 60.0) * 0.50)
                    status = AttendanceStatus.present if random.random() < prob_present else AttendanceStatus.absent

                # --- Case D: Diana Prince (Slow Improvement in Networks) ---
                elif s_idx == 3 and sub.code == "CS603":
                    prob_present = min(0.95, 0.55 + (day_idx / 60.0) * 0.40)
                    status = AttendanceStatus.present if random.random() < prob_present else AttendanceStatus.absent

                # --- Case E: Evan Wright (Subject-Specific Drop in Software Eng) ---
                elif s_idx == 4:
                    if sub.code == "CS605":
                        status = AttendanceStatus.absent if random.random() < 0.55 else AttendanceStatus.present
                    else:
                        status = AttendanceStatus.present if random.random() < 0.92 else AttendanceStatus.absent

                # --- Case F: Fiona Gallagher (Short Absence -> Recovery) ---
                elif s_idx == 5:
                    if 30 <= day_idx <= 33:
                        status = AttendanceStatus.absent
                    else:
                        status = AttendanceStatus.present

                # --- Case G: George Clark (Missing Records) ---
                elif s_idx == 6:
                    if day_idx % 4 == 0:
                        continue  # Skip inserting record to leave as "Not marked"
                    status = AttendanceStatus.present if random.random() < 0.88 else AttendanceStatus.absent

                # Regular healthy students
                else:
                    status = AttendanceStatus.present if random.random() < 0.88 else AttendanceStatus.absent

                att = Attendance(
                    student_id=student.id,
                    subject_id=sub.id,
                    date=d,
                    period=1,
                    status=status,
                    marked_by=teachers[sub_idx % len(teachers)].user_id
                )
                db.add(att)
    db.commit()

    # 6b. Seed Upcoming Exams for Class
    sub_ids = [s.id for s in subjects]
    exams_data = [
        ("Internal Test 1", date.today() + timedelta(days=10), sub_ids[:3]),
        ("Internal Test 2", date.today() + timedelta(days=25), sub_ids[3:]),
        ("End-Semester Final Examination", date.today() + timedelta(days=45), sub_ids)
    ]
    for exam_name, exam_date, covered_sub_ids in exams_data:
        ex = Exam(
            class_id=classroom.id,
            name=exam_name,
            date=exam_date,
            subject_ids=covered_sub_ids
        )
        db.add(ex)
    db.commit()

    # 7. Run AI Analytics Engine for all students & pre-create counselling cases for high risk

    print("[SEED] Running AI Pattern Analytics Engine for all students...")
    alert_count = 0
    for s in students:
        alerts = run_analytics_for_student(db, s.id)
        alert_count += len(alerts)
        for a in alerts:
            if a.level in [RiskLevel.high, RiskLevel.critical, RiskLevel.medium]:
                create_or_get_counselling_case(db, a)

    print(f"[SEED SUCCESS] Seeded 1 Mentor, 3 Teachers, 1 Class (30 Students), 5 Subjects, 60 days of attendance!")
    print(f"[SEED SUCCESS] Generated {alert_count} AI Risk Alerts & Counselling Cases!")
    print(f"\n[DEMO CREDENTIALS]")
    print(f"Mentor: mentor@example.com / password123")
    print(f"Teacher: teacher1@example.com / password123")
    print(f"Student: 1VA21CS001 / 1VA21CS001 (Alice Smith - Sudden Drop)")
    print(f"Student: 1VA21CS002 / 1VA21CS002 (Bob Jones - Continuous Absence)")
    print(f"Student: 1VA21CS005 / 1VA21CS005 (Evan Wright - Subject Drop)")

    db.close()


if __name__ == "__main__":
    seed_database()
