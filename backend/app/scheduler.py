from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.models import CounsellingCase, CaseStatus, Student, Intervention, Alert
from app.services.email import send_email


def check_and_escalate_counselling_cases():
    """Background job: escalates un-responded counselling cases >24h old to parents."""
    db: Session = SessionLocal()
    try:
        now = datetime.utcnow()
        overdue_cases = db.query(CounsellingCase).filter(
            CounsellingCase.status == CaseStatus.sent,
            CounsellingCase.deadline_at <= now
        ).all()

        for case in overdue_cases:
            student = db.query(Student).filter(Student.id == case.student_id).first()
            if student and student.parent_email:
                alert = db.query(Alert).filter(Alert.id == case.alert_id).first()
                reason_text = "; ".join(alert.explanation.get("reasons", [])) if alert and alert.explanation else "Attendance pattern alert"

                email_body = (
                    f"Dear Parent / Guardian of {student.name} ({student.usn}),\n\n"
                    f"This is an automated notification from the Academic Mentorship Department.\n"
                    f"A counselling check-in was issued to {student.name} regarding attendance concerns ({reason_text}). "
                    f"As 24 hours have passed without a response, we are informing you so we can work together to ensure "
                    f"your ward stays on track academically.\n\n"
                    f"Please contact the mentor or department if you have any questions.\n\n"
                    f"Sincerely,\nAcademic Mentorship Department"
                )
                subject = f"[Important] Academic Attendance Notice for {student.name}"
                send_email(student.parent_email, subject, email_body)

            case.status = CaseStatus.escalated
            case.escalated_at = now

            # Log intervention
            intervention = Intervention(
                student_id=case.student_id,
                alert_id=case.alert_id,
                staff_id=None,
                type="parent_email_auto",
                notes="Automated 24h deadline escalation to parent email",
                date=now.date(),
                outcome="Parent notified via automated escalation"
            )
            db.add(intervention)

        db.commit()
    except Exception as e:
        print(f"[SCHEDULER ERROR] Failed during escalation check: {e}")
        db.rollback()
    finally:
        db.close()


def run_email_queue_job():
    """Background job: processes pending items in the immediate EmailQueue every 1 minute."""
    db: Session = SessionLocal()
    try:
        from app.services.absence_followup import process_email_queue
        process_email_queue(db)
    except Exception as e:
        print(f"[SCHEDULER ERROR] Failed during email queue processing: {e}")
        db.rollback()
    finally:
        db.close()


def run_absence_followup_job():
    """Background job: processes due student and parent absence follow-up emails every 15 minutes."""
    db: Session = SessionLocal()
    try:
        from app.services.absence_followup import process_absence_followups
        process_absence_followups(db)
    except Exception as e:
        print(f"[SCHEDULER ERROR] Failed during absence follow-up processing: {e}")
        db.rollback()
    finally:
        db.close()


def start_scheduler():
    """Starts the APScheduler background scheduler."""
    scheduler = BackgroundScheduler()
    scheduler.add_job(run_email_queue_job, 'interval', minutes=1, id='email_queue_1m_check')
    scheduler.add_job(check_and_escalate_counselling_cases, 'interval', minutes=30, id='counselling_24h_check')
    scheduler.add_job(run_absence_followup_job, 'interval', minutes=15, id='absence_followup_15m_check')
    scheduler.start()
    print("[SCHEDULER] APScheduler started for 1m email queue processing, 24h counselling escalation, and 15m follow-up automation.")
    return scheduler


