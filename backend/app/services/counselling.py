import uuid
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from anthropic import Anthropic

from app.models.models import (
    Student, Alert, CounsellingCase, CounsellingMessage, CaseStatus, RiskLevel
)
from app.services.email import send_email
from app.config import get_settings

settings = get_settings()


def generate_counselling_message(student: Student, alert: Alert) -> str:
    """Generates empathetic AI counselling message using Anthropic Claude API or fallback."""
    reasons_str = "; ".join(alert.explanation.get("reasons", ["Attendance irregularity flagged"]))
    
    prompt = f"""You are a caring, empathetic academic mentor at a college.
Write a supportive, non-punitive, personalized counselling check-in message to student {student.name}.

Student Details:
- Name: {student.name}
- USN: {student.usn}
- Risk Level: {alert.level.value if hasattr(alert.level, 'value') else alert.level}
- Detected Pattern Reasons: {reasons_str}

Guidelines:
- Be encouraging and empathetic.
- Frame attendance as crucial for their learning and success.
- Ask if they are facing any challenges (health, personal, academic) and how the department can support them.
- Keep it concise (3 short paragraphs maximum).
- Ask them to reply directly to this message or meet their mentor.
"""

    if settings.ANTHROPIC_API_KEY:
        try:
            client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            res = client.messages.create(
                model=settings.ANTHROPIC_MODEL,
                max_tokens=350,
                messages=[{"role": "user", "content": prompt}]
            )
            return res.content[0].text.strip()
        except Exception as e:
            print(f"[ANTHROPIC API ERROR] Fallback used: {e}")

    # Fallback empathetic template
    return (
        f"Dear {student.name},\n\n"
        f"We noticed that your recent attendance has shown some changes ({reasons_str}). "
        f"We are reaching out because your learning experience and well-being matter to us.\n\n"
        f"If you are experiencing any difficulties—whether academic, personal, or health-related—please "
        f"know that your mentor and teachers are here to help. Please reply to this message so we can discuss "
        f"how to best support you in getting back on track.\n\n"
        f"Warm regards,\nAcademic Mentorship Team"
    )


def create_or_get_counselling_case(db: Session, alert: Alert) -> CounsellingCase:
    """Creates a counselling case for a flagged student alert."""
    existing = db.query(CounsellingCase).filter(CounsellingCase.alert_id == alert.id).first()
    if existing:
        return existing

    student = db.query(Student).filter(Student.id == alert.student_id).first()
    if not student:
        raise ValueError("Student not found")

    message_body = generate_counselling_message(student, alert)
    token = str(uuid.uuid4())[:8]

    now = datetime.utcnow()
    deadline = now + timedelta(hours=settings.COUNSELLING_DEADLINE_HOURS)

    case = CounsellingCase(
        alert_id=alert.id,
        student_id=student.id,
        message=message_body,
        status=CaseStatus.draft,
        thread_token=token,
        deadline_at=deadline
    )
    db.add(case)
    db.commit()
    db.refresh(case)

    # Initial AI message in thread
    msg = CounsellingMessage(
        case_id=case.id,
        sender="ai",
        channel="app",
        body=message_body
    )
    db.add(msg)
    db.commit()

    # If AUTO_SEND is true, send immediately
    if settings.COUNSELLING_AUTO_SEND:
        send_counselling_case(db, case.id)

    return case


def send_counselling_case(db: Session, case_id: int) -> CounsellingCase:
    """Sends the counselling message via email to student and sets status to SENT."""
    case = db.query(CounsellingCase).filter(CounsellingCase.id == case_id).first()
    if not case:
        raise ValueError("Case not found")

    student = db.query(Student).filter(Student.id == case.student_id).first()
    if student and student.email:
        subject = f"[Academic Check-in] Attendance Support (Ref: {case.thread_token})"
        send_email(student.email, subject, case.message)

    case.status = CaseStatus.sent
    case.sent_at = datetime.utcnow()
    case.deadline_at = datetime.utcnow() + timedelta(hours=settings.COUNSELLING_DEADLINE_HOURS)
    db.commit()
    db.refresh(case)
    return case
