import sys
import os
import uuid
from typing import Optional, Tuple, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

try:
    ml_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../ml"))
    if ml_path not in sys.path:
        sys.path.append(ml_path)
    from src.predict import predict_counsel
except Exception as e:
    predict_counsel = None
    print(f"Failed to import predict_counsel: {e}")

from app.models.models import (
    Student, Alert, CounsellingCase, CounsellingMessage, CaseStatus, RiskLevel,
    AbsenceReason, Subject, Attendance, AttendanceStatus, Remark, Role
)
from app.services.email import send_email
from app.config import get_settings
from app.services.openrouter_client import call_openrouter

settings = get_settings()


def get_student_attendance_summary_text(db: Session, student_id: int) -> str:
    """Returns formatted per-subject attendance percentages and 75% cutoff status."""
    if not db:
        return "Attendance data unavailable."

    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        return "Student not found."

    subjects = db.query(Subject).filter(Subject.class_id == student.class_id).all()
    records = db.query(Attendance).filter(Attendance.student_id == student_id).all()

    total_all = len(records)
    att_all = sum(1 for r in records if r.status == AttendanceStatus.present)
    overall_pct = (att_all / total_all * 100.0) if total_all > 0 else 100.0

    lines = [f"Overall Attendance: {overall_pct:.1f}% (Required Cutoff: {settings.ATTENDANCE_THRESHOLD}%)"]

    from app.services.analytics import calculate_classes_needed
    for s in subjects:
        sub_recs = [r for r in records if r.subject_id == s.id]
        sub_tot = len(sub_recs)
        sub_att = sum(1 for r in sub_recs if r.status == AttendanceStatus.present)
        sub_pct = (sub_att / sub_tot * 100.0) if sub_tot > 0 else 100.0

        calc = calculate_classes_needed(sub_att, sub_tot, settings.ATTENDANCE_THRESHOLD)
        needed = calc["classes_needed"]
        lines.append(f"- {s.name} ({s.code}): {sub_pct:.1f}% (Attended {sub_att}/{sub_tot}). Classes needed to reach {settings.ATTENDANCE_THRESHOLD}%: {needed}")

    return "\n".join(lines)


def get_student_absence_details(db: Session, student_id: int) -> str:
    """Returns recent absence dates, subjects, and reasons submitted by the student."""
    if not db:
        return "No information found"

    reasons = db.query(AbsenceReason).filter(AbsenceReason.student_id == student_id).order_by(AbsenceReason.date.desc()).all()
    if not reasons:
        return "No information found"

    lines = []
    for r in reasons[:5]:
        sub_name = "General"
        if r.subject_id:
            s = db.query(Subject).filter(Subject.id == r.subject_id).first()
            if s:
                sub_name = f"{s.name} ({s.code})"
        lines.append(f"- Date: {r.date}, Subject: {sub_name}, Category: {r.category}, Reason: '{r.reason}'")
    return "\n".join(lines)


def get_case_history_text(db: Session, case_id: int) -> str:
    """Returns formatted history of messages in a counselling case."""
    if not db or not case_id:
        return "(No prior messages)"

    messages = db.query(CounsellingMessage).filter(CounsellingMessage.case_id == case_id).order_by(CounsellingMessage.created_at.asc()).all()
    if not messages:
        return "(No prior messages in thread)"

    formatted = []
    for m in messages:
        sender_label = "Student" if m.sender == "student" else ("Counsellor" if m.sender == "ai" else "Staff/Mentor")
        formatted.append(f"{sender_label}: {m.body}")
    return "\n".join(formatted)


def generate_counselling_message(student: Student, alert: Alert, db: Session = None) -> str:
    """Generates an initial empathetic check-in message acting as a warm human college counsellor."""
    reasons_str = "; ".join(alert.explanation.get("reasons", ["Attendance irregularity flagged"])) if alert and alert.explanation else "Attendance drop detected"

    first_name = student.name.split()[0] if student.name else "Student"

    prediction = {}
    if predict_counsel and db:
        try:
            from app.routers.ml_counsel import compute_attendance_features
            features = compute_attendance_features(db, student.id)
            prediction = predict_counsel(features, reasons_str)
        except Exception as e:
            print(f"[ML Counsel Error] {e}")

    # Crisis check
    if prediction.get("is_crisis"):
        return (
            f"Dear {first_name},\n\n"
            f"We care deeply about your well-being, and your health and safety are our top priority. "
            f"Please know that you are not alone and immediate support is available to help you right now:\n\n"
            f"• iCall Psychosocial Helpline: 9152987821\n"
            f"• Vandrevala Foundation (24x7): 1860-2662-345 / 9999 666 555\n"
            f"• National Emergency Services: 112\n\n"
            f"These services are confidential and free. Please reach out to them or contact your mentor immediately."
        )

    att_summary = get_student_attendance_summary_text(db, student.id) if db else "Attendance details being evaluated."
    absence_details = get_student_absence_details(db, student.id) if db else "Absence pattern noted."

    system_prompt = (
        f"You are a warm, experienced human college counsellor writing directly to student {first_name}.\n"
        f"You are reaching out for an initial 1-on-1 supportive check-in about their recent attendance.\n\n"
        f"GUIDELINES:\n"
        f"1. Tone: Write in a warm, conversational, natural human counsellor tone (80 to 150 words total). Use natural paragraphs. DO NOT use headings, bullet lists, markdown bold titles, or robotic boilerplate.\n"
        f"2. Address: Address {first_name} warmly by first name.\n"
        f"3. Content: Acknowledge the attendance notice naturally, ask if they are facing any health, personal, or academic challenges, and ask at most ONE gentle follow-up question to start the dialogue.\n"
        f"4. Cleanliness: NEVER output raw ML labels, category names (like 'Unknown'), confidence scores, 'Noted attendance factors', or mentor instructions."
    )

    user_prompt = (
        f"STUDENT: {student.name} ({student.usn})\n"
        f"ATTENDANCE CONTEXT:\n{att_summary}\n\n"
        f"ABSENCE REASONS:\n{absence_details}\n\n"
        f"REASON FLAGGED: {reasons_str}\n\n"
        f"Write your initial check-in message to {first_name}:"
    )

    res, err = call_openrouter(user_prompt, system_prompt=system_prompt, json_mode=False, timeout_seconds=18)
    if res and isinstance(res, str) and res.strip():
        return res.strip()

    # Friendly error response if AI call fails - no template fallback!
    return "Couldn't generate a check-in message, please try again."


def generate_counselling_reply(student: Student, case: CounsellingCase, student_reply: str, db: Session = None) -> tuple[str, dict]:
    """Generates an AI counselling reply acting as a warm human college counsellor, responding to student input and thread history."""
    first_name = student.name.split()[0] if student.name else "Student"

    prediction = {}
    if predict_counsel and db:
        try:
            from app.routers.ml_counsel import compute_attendance_features
            features = compute_attendance_features(db, student.id)
            prediction = predict_counsel(features, student_reply)
        except Exception as e:
            print(f"[ML Predict Error in Reply] {e}")

    # Safety protocol for crisis / distress
    if prediction.get("is_crisis"):
        msg = (
            f"Dear {first_name},\n\n"
            f"Your safety and well-being are our highest priority, and we care about what you are experiencing. "
            f"Please know that you are not alone and support is immediately available:\n\n"
            f"• iCall Psychosocial Helpline: 9152987821\n"
            f"• Vandrevala Foundation (24x7): 1860-2662-345 / 9999 666 555\n"
            f"• National Emergency Services: 112\n\n"
            f"These services are free, confidential, and available right now. Please reach out to one of these resources or contact your mentor immediately."
        )
        return msg, prediction

    att_summary = get_student_attendance_summary_text(db, student.id) if db else ""
    absence_details = get_student_absence_details(db, student.id) if db else ""
    history_text = get_case_history_text(db, case.id if case else None) if db else ""

    system_prompt = (
        f"You are a warm, empathetic, and experienced human college counsellor writing directly to student {first_name}.\n"
        f"You are having an ongoing 1-on-1 supportive conversation with {first_name}.\n\n"
        f"CRITICAL COUNSELLOR GUIDELINES:\n"
        f"1. Tone & Format: Write as a warm, genuine human counsellor in short, natural paragraphs (about 80 to 150 words total). "
        f"Do NOT use markdown headings, bullet points, numbered lists, section headers, or robotic template phrases.\n"
        f"2. Address: Address {first_name} warmly by first name.\n"
        f"3. Acknowledge & Respond: Directly respond to what {first_name} actually said in their message without repeating yourself. "
        f"Ask at most ONE gentle follow-up question to keep the conversation going naturally.\n"
        f"4. Internal Reason Assessment (Judge internally - NEVER show the words 'genuine' or 'not genuine' to the student):\n"
        f"   - Genuine reason (illness, fever, family emergency, bereavement, transport breakdown, official event): "
        f"Respond with empathy and practical help. Suggest submitting proof if required, speaking to the subject teacher about missed work, "
        f"and how to catch up. Do NOT push or pressure them.\n"
        f"   - Weak or Not Genuine reason (no reason, 'didn't feel like it', oversleeping, outings, repeated unexplained absences): "
        f"Respond kindly but honestly. Do NOT shame or accuse. Persuade {first_name} to attend classes using their REAL attendance numbers "
        f"(e.g., 'Maths is at 68%, and you need 75%, so attending the next 6 classes will bring you back on track'). Explain consequences for exam eligibility, "
        f"emphasize the value of consistency, and gently guide them to make a small, doable commitment (e.g., 'Can you promise to attend the next three Maths classes?').\n"
        f"   - Unclear reason: Ask a caring open question to understand what is going on.\n"
        f"5. Privacy & Cleanliness: NEVER show raw ML labels (such as 'Unknown' or category names), confidence scores, 'Noted attendance factors', "
        f"bullet lists of factors, mentor instructions, or 'AI Counselling Support' boilerplate.\n"
        f"6. Respond naturally based on the full conversation history."
    )

    user_prompt = (
        f"STUDENT DETAILS:\n"
        f"- Name: {student.name}\n"
        f"- USN: {student.usn}\n\n"
        f"PER-SUBJECT ATTENDANCE DATA & 75% THRESHOLD:\n"
        f"{att_summary}\n\n"
        f"RECORDED ABSENCES & REASONS:\n"
        f"{absence_details}\n\n"
        f"PRIVATE ML DIAGNOSTIC HINTS (Use internally ONLY - DO NOT mention to student):\n"
        f"- Problem Category Hint: {prediction.get('problem_category', 'General Check-in')}\n"
        f"- Emotion Hint: {prediction.get('emotion', 'Concerned')}\n"
        f"- Top Factors Hint: {', '.join(prediction.get('top_factors', []))}\n\n"
        f"CONVERSATION HISTORY:\n"
        f"{history_text}\n\n"
        f"LATEST STUDENT INPUT:\n"
        f"{student_reply}\n\n"
        f"Write your response as the human college counsellor to {first_name}:"
    )

    res, err = call_openrouter(user_prompt, system_prompt=system_prompt, json_mode=False, timeout_seconds=18)
    if res and isinstance(res, str) and res.strip():
        return res.strip(), prediction

    # Failure handling: short friendly retry message, no robotic template!
    return "Couldn't generate a reply, please try again.", prediction


def generate_and_save_counselling_summary(db: Session, case_id: int) -> Optional[Remark]:
    """
    Generates a 3-5 line concise Counselling Summary for a thread and saves/updates
    it in the student's Remarks table (visible to mentors).
    """
    if not db or not case_id:
        return None

    case = db.query(CounsellingCase).filter(CounsellingCase.id == case_id).first()
    if not case:
        return None

    student = db.query(Student).filter(Student.id == case.student_id).first()
    if not student:
        return None

    absence_details = get_student_absence_details(db, student.id)
    history_text = get_case_history_text(db, case.id)

    # Crisis check
    is_crisis = any(
        "helpline" in m.body.lower() or "icall" in m.body.lower() or "vandrevala" in m.body.lower()
        for m in case.messages if m.sender == "ai"
    )

    summary_system_prompt = (
        "You are an academic counselling assistant summarizing student check-in conversations for college mentors.\n"
        "Write a concise summary (3 to 5 lines) that will be saved in the student's Remarks section.\n"
        "STRICT RULES:\n"
        "1. Base your summary ONLY on what was actually said in the conversation thread and absence records.\n"
        "2. Do NOT invent dates, reasons, or commitments that are not present in the thread.\n"
        "3. Follow this exact format:\n"
        "Counselling Summary\n"
        "• Date(s) & Subject(s): [List dates/subjects from records/thread or 'No information found']\n"
        "• Reason Given: [State the student's explanation or 'No information found']\n"
        "• Guidance & Agreement: [Brief summary of counsellor advice and student response/commitment]\n"
        "• Status: [Select one: 'Student committed to attend' | 'Needs mentor follow-up' | 'Distress flagged' | 'Awaiting student response']"
    )

    summary_user_prompt = (
        f"STUDENT: {student.name} ({student.usn})\n"
        f"ABSENCE RECORDS:\n{absence_details}\n\n"
        f"CONVERSATION THREAD:\n{history_text}\n\n"
        f"Generate the 3-5 line Counselling Summary:"
    )

    res, err = call_openrouter(summary_user_prompt, system_prompt=summary_system_prompt, json_mode=False, timeout_seconds=15)

    now_str = datetime.now().strftime("%b %d, %Y at %I:%M %p")
    header = f"Counselling Summary (Ref: {case.thread_token})"

    if res and isinstance(res, str) and res.strip():
        summary_content = res.strip()
        if not summary_content.startswith("Counselling Summary"):
            summary_content = f"{header}\n{summary_content}"
        summary_text = f"{summary_content}\n• Updated: {now_str}"
    else:
        # Fallback structured summary if AI call fails
        status_str = "Distress flagged" if is_crisis else "Needs mentor follow-up"
        summary_text = (
            f"{header}\n"
            f"• Date(s) & Subject(s): {absence_details.splitlines()[0] if absence_details else 'No information found'}\n"
            f"• Reason Given: Recorded in thread\n"
            f"• Guidance & Agreement: Counsellor check-in conducted.\n"
            f"• Status: {status_str}\n"
            f"• Updated: {now_str}"
        )

    # Find existing remark entry for this counselling case / thread
    existing_remark = db.query(Remark).filter(
        Remark.student_id == student.id,
        Remark.text.like(f"%Ref: {case.thread_token}%")
    ).first()

    # Find mentor user ID for author_id
    mentor_user_id = None
    if student.classroom and student.classroom.mentor:
        mentor_user_id = student.classroom.mentor.user_id

    if not mentor_user_id:
        from app.models.models import User
        mentor_u = db.query(User).filter(User.role == Role.mentor).first()
        mentor_user_id = mentor_u.id if mentor_u else (student.user_id or 1)

    if existing_remark:
        existing_remark.text = summary_text
        existing_remark.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing_remark)
        return existing_remark
    else:
        new_remark = Remark(
            student_id=student.id,
            author_id=mentor_user_id,
            role=Role.mentor,
            text=summary_text
        )
        db.add(new_remark)
        db.commit()
        db.refresh(new_remark)
        return new_remark


def create_or_get_counselling_case(db: Session, alert: Alert) -> CounsellingCase:
    """Creates a counselling case for a flagged student alert."""
    existing = db.query(CounsellingCase).filter(CounsellingCase.alert_id == alert.id).first()
    if existing:
        return existing

    student = db.query(Student).filter(Student.id == alert.student_id).first()
    if not student:
        raise ValueError("Student not found")

    message_body = generate_counselling_message(student, alert, db=db)
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

    # Generate initial Counselling Summary in mentor's Remarks
    try:
        generate_and_save_counselling_summary(db, case.id)
    except Exception as e:
        print(f"[Error generating initial counselling summary] {e}")

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

