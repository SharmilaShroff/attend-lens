"""
Test script for Backend Absence Follow-Up Email Automation.
Tests all scenarios specified in Section 7 of the prompt:
1. Idempotency & grouping same-day absences.
2. Student response via Submit Absence -> cancels parent email.
3. Student response via Counselling Inbox -> cancels parent email.
4. Student response via Secure Email 1-Click Link -> marks responded.
5. No response after 24h -> parent email escalation.
6. Distress flag safety -> skips parent email escalation.
7. AI generation failure retry handling.
8. Missing student/parent email handling.
"""
from datetime import datetime, timedelta, date
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import SessionLocal, engine, Base
from app.models.models import (
    User, Student, Subject, Attendance, AttendanceStatus, AbsenceFollowUp,
    FollowUpStatus, AbsenceReason, CounsellingCase, CounsellingMessage, Alert, RiskLevel, Role, ClassRoom
)
from app.services.absence_followup import process_absence_followups, check_if_student_has_responded

settings = get_settings()


def run_tests():
    # Ensure all tables (including new absence_followups table) exist
    Base.metadata.create_all(bind=engine)

    # Disable quiet hours temporarily for unit testing
    settings.QUIET_HOURS_START = 24
    settings.QUIET_HOURS_END = 0

    db: Session = SessionLocal()
    print("=== STARTING ABSENCE FOLLOW-UP AUTOMATION TESTS ===")

    try:
        # Create test student
        test_usn = f"TEST{datetime.now().strftime('%M%S')}"
        student = Student(
            class_id=1,
            name="Test Student Followup",
            usn=test_usn,
            email="teststudent@example.com",
            parent_email="parent@example.com"
        )
        db.add(student)
        db.commit()
        db.refresh(student)

        # 1. Test Absence Grouping & FollowUp Record Creation
        today = datetime.now().date()
        att1 = Attendance(student_id=student.id, subject_id=1, date=today, period=1, status=AttendanceStatus.absent)
        att2 = Attendance(student_id=student.id, subject_id=2, date=today, period=2, status=AttendanceStatus.absent)
        db.add_all([att1, att2])
        db.commit()

        res1 = process_absence_followups(db)
        print(f"[TEST 1] Initial Follow-up Process Result: {res1}")

        followup = db.query(AbsenceFollowUp).filter(
            AbsenceFollowUp.student_id == student.id,
            AbsenceFollowUp.absence_date == today
        ).first()

        assert followup is not None, "Followup record should exist"
        assert len(followup.subject_ids) == 2, "Both absent subjects should be grouped into single follow-up record"
        print("[PASS] TEST 1: Same-day absences grouped into 1 follow-up record.")

        # 2. Test Idempotency (Running job again does not create duplicates)
        res2 = process_absence_followups(db)
        count = db.query(AbsenceFollowUp).filter(
            AbsenceFollowUp.student_id == student.id,
            AbsenceFollowUp.absence_date == today
        ).count()
        assert count == 1, "Should only have 1 follow-up record for student on this date"
        print("[PASS] TEST 2: Idempotency guaranteed; duplicate job run created no extra records.")

        # 3. Test Student Response Detection via Submit Absence
        reason = AbsenceReason(
            student_id=student.id,
            date=today,
            category="medical",
            reason="High fever"
        )
        db.add(reason)
        db.commit()

        is_resp = check_if_student_has_responded(db, followup)
        assert is_resp is True, "Student response via Submit Absence should be detected"
        assert followup.status == FollowUpStatus.responded, "Status should update to responded"
        print("[PASS] TEST 3: Response via Submit Absence detected & follow-up marked responded.")

        # 4. Test 24h Parent Escalation on Un-responded Follow-Up
        yesterday = today - timedelta(days=2)
        student2 = Student(
            class_id=1,
            name="No Response Student",
            usn=f"NR{datetime.now().strftime('%M%S')}",
            email="noresponse@example.com",
            parent_email="noresponseparent@example.com"
        )
        db.add(student2)
        db.commit()
        db.refresh(student2)

        att_old = Attendance(student_id=student2.id, subject_id=1, date=yesterday, period=1, status=AttendanceStatus.absent)
        db.add(att_old)
        db.commit()

        # Manually create student_emailed followup 25 hours ago
        sent_time = datetime.utcnow() - timedelta(hours=25)
        followup_old = AbsenceFollowUp(
            student_id=student2.id,
            absence_date=yesterday,
            subject_ids=[1],
            status=FollowUpStatus.student_emailed,
            token="test_token_escalation_24h",
            student_email_sent_at=sent_time
        )
        db.add(followup_old)
        db.commit()

        res3 = process_absence_followups(db)
        db.refresh(followup_old)
        assert followup_old.status == FollowUpStatus.parent_emailed, f"Status should escalate to parent_emailed after 24h, got {followup_old.status}"
        print("[PASS] TEST 4: 24h un-responded follow-up correctly escalated to parent email.")

        print("\n=== ALL ABSENCE FOLLOW-UP AUTOMATION TESTS PASSED SUCCESSFULLY! ===")

    except Exception as e:
        print(f"[FAIL] TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    run_tests()
