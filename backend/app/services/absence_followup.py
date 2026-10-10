"""
Absence Follow-Up Service for Attend Lens Backend.
Manages automated 2-step absence follow-up emails (student email -> 24h wait -> parent email).
Uses existing OpenRouter helper for student emails, respects quiet hours, checks responses,
retries failed sends up to 3 times, and ensures idempotency and parent privacy.
"""
import secrets
import time as pytime
from datetime import datetime, timedelta, date, time
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.models import (
    Student, Attendance, AttendanceStatus, Subject, AbsenceReason,
    CounsellingCase, CounsellingMessage, AbsenceFollowUp, FollowUpStatus, User, Role,
    EmailQueue, QueueRecipientType, QueueStatus
)
from app.services.email import send_email, validate_email
from app.services.openrouter_client import call_openrouter

settings = get_settings()


def is_quiet_hours(now_dt: Optional[datetime] = None) -> bool:
    """
    Checks if the current time falls inside quiet hours window (default 9 PM to 7 AM).
    """
    if now_dt is None:
        now_dt = datetime.now()

    hour = now_dt.hour
    start = settings.QUIET_HOURS_START  # Default 21 (9 PM)
    end = settings.QUIET_HOURS_END      # Default 7 (7 AM)

    if start > end:
        # Crosses midnight (e.g. 21:00 to 07:00)
        return hour >= start or hour < end
    else:
        return start <= hour < end


def create_or_sync_absence_followups(db: Session, target_date: Optional[date] = None) -> int:
    """
    Scans absent attendance records and groups multiple absences on the same day
    into a single AbsenceFollowUp record per student per day.
    """
    if target_date is None:
        target_date = datetime.now().date()

    # Query all absent records on target_date
    absent_records = db.query(Attendance).filter(
        Attendance.date == target_date,
        Attendance.status == AttendanceStatus.absent
    ).all()

    if not absent_records:
        return 0

    # Group subject IDs by student_id
    student_absences: Dict[int, List[int]] = {}
    for rec in absent_records:
        student_absences.setdefault(rec.student_id, []).append(rec.subject_id)

    count = 0
    for student_id, subject_ids in student_absences.items():
        unique_subject_ids = list(set(subject_ids))

        # Check existing follow-up record for student + date
        existing = db.query(AbsenceFollowUp).filter(
            AbsenceFollowUp.student_id == student_id,
            AbsenceFollowUp.absence_date == target_date
        ).first()

        if existing:
            # Update subject list if new subjects were marked absent
            current_subjects = list(set(existing.subject_ids or [] + unique_subject_ids))
            existing.subject_ids = current_subjects
        else:
            token = secrets.token_urlsafe(32)
            token_expires = datetime.utcnow() + timedelta(days=7)

            followup = AbsenceFollowUp(
                student_id=student_id,
                absence_date=target_date,
                subject_ids=unique_subject_ids,
                status=FollowUpStatus.pending,
                token=token,
                token_expires_at=token_expires
            )
            db.add(followup)
            count += 1

    db.commit()
    return count


def check_if_student_has_responded(db: Session, followup: AbsenceFollowUp) -> bool:
    """
    Checks if the student has responded to this absence via:
    1. A reason submitted in Submit Absence (AbsenceReason)
    2. A message sent in the AI Counselling Inbox (CounsellingMessage)
    3. A click/submit via secure email reply link
    """
    if followup.status == FollowUpStatus.responded:
        return True

    # 1. Check Submit Absence (AbsenceReason)
    reason_submitted = db.query(AbsenceReason).filter(
        AbsenceReason.student_id == followup.student_id,
        AbsenceReason.date == followup.absence_date
    ).first()

    if reason_submitted:
        followup.status = FollowUpStatus.responded
        followup.responded_at = reason_submitted.created_at or datetime.utcnow()
        followup.response_source = "submit_absence"
        db.commit()
        return True

    # 2. Check AI Counselling Inbox message
    counselling_msg = db.query(CounsellingMessage).join(CounsellingCase).filter(
        CounsellingCase.student_id == followup.student_id,
        CounsellingMessage.sender == "student",
        CounsellingMessage.created_at >= datetime.combine(followup.absence_date, time.min)
    ).first()

    if counselling_msg:
        followup.status = FollowUpStatus.responded
        followup.responded_at = counselling_msg.created_at
        followup.response_source = "counselling_inbox"
        db.commit()
        return True

    return False


def has_distress_flag(db: Session, student_id: int) -> bool:
    """
    Checks if the student's counselling thread or messages show serious distress or self-harm.
    If flagged, parent email must be skipped to protect student safety & trust.
    """
    keywords = [k.strip().lower() for k in settings.ML_CRISIS_KEYWORDS.split(",") if k.strip()]
    keywords.extend(["helpline", "icall", "vandrevala", "emergency", "self-harm"])

    cases = db.query(CounsellingCase).filter(CounsellingCase.student_id == student_id).all()
    for c in cases:
        for m in c.messages:
            text_lower = m.body.lower()
            if any(kw in text_lower for kw in keywords):
                return True

    return False


def get_subject_names_and_pct(db: Session, student: Student, subject_ids: List[int]) -> Tuple[str, str]:
    """Generates formatted subject names and attendance stats vs 75% cutoff."""
    if not subject_ids:
        return "General Class", "Attendance records currently updating."

    subjects = db.query(Subject).filter(Subject.id.in_(subject_ids)).all()
    sub_names = ", ".join([f"{s.name} ({s.code})" for s in subjects]) if subjects else "General Class"

    records = db.query(Attendance).filter(Attendance.student_id == student.id).all()
    stats_lines = []

    for s in subjects:
        sub_recs = [r for r in records if r.subject_id == s.id]
        sub_tot = len(sub_recs)
        sub_att = sum(1 for r in sub_recs if r.status == AttendanceStatus.present)
        sub_pct = (sub_att / sub_tot * 100.0) if sub_tot > 0 else 100.0
        stats_lines.append(f"- {s.name} ({s.code}): {sub_pct:.1f}% (Required: {settings.ATTENDANCE_THRESHOLD}%)")

    stats_str = "\n".join(stats_lines)
    return sub_names, stats_str


def generate_student_followup_email_text(db: Session, followup: AbsenceFollowUp) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Generates warm human counsellor student email using OpenRouter API.
    Returns (subject, text_body, html_body). Returns (None, None, None) if AI generation fails.
    """
    student = db.query(Student).filter(Student.id == followup.student_id).first()
    if not student:
        return None, None, None

    first_name = student.name.split()[0] if student.name else "Student"
    sub_names, stats_str = get_subject_names_and_pct(db, student, followup.subject_ids or [])
    absence_date_str = followup.absence_date.strftime("%A, %b %d, %Y")

    base_url = settings.APP_BASE_URL.rstrip("/")
    reply_link = f"{base_url}/api/student/absence-followup/reply/{followup.token}"

    system_prompt = (
        f"You are a warm, supportive, and experienced human college counsellor writing a follow-up email to student {first_name}.\n"
        f"They were absent on {absence_date_str} for: {sub_names}.\n\n"
        f"GUIDELINES:\n"
        f"1. Tone: Warm, human, empathetic, conversational paragraphs (80 to 140 words). Address {first_name} by first name.\n"
        f"2. Facts: Mention the date of absence ({absence_date_str}), the subject(s) missed ({sub_names}), and their current attendance vs the {settings.ATTENDANCE_THRESHOLD}% cutoff threshold.\n"
        f"3. Request: Kindly ask them to reply within 24 hours to let you know the reason or if they need any support.\n"
        f"4. Cleanliness: NO robotic templates, NO raw ML labels or confidence scores, NO markdown headings or bullet lists of internal codes.\n"
        f"5. Do NOT output any login instructions or technical links in your generated paragraph."
    )

    user_prompt = (
        f"STUDENT NAME: {student.name}\n"
        f"ABSENCE DATE: {absence_date_str}\n"
        f"SUBJECTS MISSED: {sub_names}\n"
        f"ATTENDANCE STATS:\n{stats_str}\n\n"
        f"Write your email text to {first_name}:"
    )

    res, err = call_openrouter(user_prompt, system_prompt=system_prompt, json_mode=False, timeout_seconds=18)

    # If OpenRouter API call fails, return None to trigger retry rather than sending broken email
    if not res or not isinstance(res, str) or not res.strip():
        print(f"[FOLLOWUP EMAIL AI ERROR] Failed to generate email text: {err}")
        return None, None, None

    email_intro = res.strip()

    email_subject = f"Attendance Follow-up for {absence_date_str} ({sub_names})"

    text_body = (
        f"{email_intro}\n\n"
        f"--------------------------------------------------\n"
        f"Please share your reason for this absence by clicking your secure 1-click reply link below (no login required, valid for 24 hours):\n"
        f"{reply_link}\n\n"
        f"Or reply directly through your Student Dashboard AI Counselling Inbox.\n"
        f"--------------------------------------------------\n\n"
        f"Warm regards,\n"
        f"Academic Mentorship & Counselling Department"
    )

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family: sans-serif; background-color: #f4f8f5; padding: 20px; color: #143628;">
      <div style="max-width: 580px; margin: 0 auto; background: #ffffff; padding: 28px; border-radius: 16px; border: 1px solid #1e4d3b20;">
        <h2 style="color: #1e4d3b; margin-top: 0;">Academic Attendance Follow-up</h2>
        <div style="font-size: 14px; line-height: 1.6; whitespace: pre-line;">{email_intro}</div>
        
        <div style="margin-top: 24px; padding: 20px; background-color: #e8f5e9; border-radius: 12px; text-align: center;">
          <p style="font-size: 13px; font-weight: bold; color: #143628; margin-bottom: 12px;">
            Please reply within 24 hours to keep your mentor updated:
          </p>
          <a href="{reply_link}" style="display: inline-block; background-color: #1e4d3b; color: #ffffff; font-weight: bold; font-size: 13px; padding: 12px 24px; text-decoration: none; border-radius: 8px;">
            Submit Absence Reason (1-Click Reply)
          </a>
        </div>
        
        <p style="font-size: 11px; color: #666; margin-top: 24px; text-align: center;">
          Attend Lens Academic Mentorship Department &bull; Ref: {followup.token[:8]}
        </p>
      </div>
    </body>
    </html>
    """

    return email_subject, text_body, html_body


def generate_parent_followup_email_text(db: Session, followup: AbsenceFollowUp) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Generates polite, factual, non-accusatory parent email.
    Includes student name, dates, subjects, attendance vs 75% cutoff, and mentor contact info.
    PRIVACY: Does NOT include counselling conversation details, ML predictions, emotions, remarks, or private reasons.
    """
    student = db.query(Student).filter(Student.id == followup.student_id).first()
    if not student:
        return None, None, None

    sub_names, stats_str = get_subject_names_and_pct(db, student, followup.subject_ids or [])
    absence_date_str = followup.absence_date.strftime("%A, %b %d, %Y")

    mentor_contact = "Academic Mentorship Department (Email: mentor@attendlens.edu)"
    if student.classroom and student.classroom.mentor and student.classroom.mentor.user:
        u = student.classroom.mentor.user
        mentor_contact = f"{u.name} (Email: {u.email or 'mentor@attendlens.edu'})"

    subject = f"[Important] Class Attendance Notice for {student.name} ({student.usn})"

    text_body = (
        f"Dear Parent / Guardian of {student.name},\n\n"
        f"This is an official attendance notice from the Academic Mentorship Department regarding your ward, {student.name} (USN: {student.usn}).\n\n"
        f"Absence Record Details:\n"
        f"• Date of Absence: {absence_date_str}\n"
        f"• Subject(s) Missed: {sub_names}\n\n"
        f"Current Subject Attendance Status:\n"
        f"{stats_str}\n\n"
        f"Our department contacted {student.name} earlier regarding this absence, but we have not received a response within the past 24 hours. "
        f"Maintaining regular attendance above the required 75% threshold is essential for academic progress and exam eligibility.\n\n"
        f"We kindly request you to speak with {student.name} and encourage regular class attendance.\n\n"
        f"If you have any questions or require assistance, please contact your ward's mentor:\n"
        f"Mentor Contact: {mentor_contact}\n\n"
        f"Sincerely,\n"
        f"Academic Mentorship Department\n"
        f"Attend Lens Academic System\n\n"
        f"---\n"
        f"Notice: You received this official academic notification as the registered parent/guardian contact for {student.name}."
    )

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family: sans-serif; background-color: #f8faf9; padding: 20px; color: #143628;">
      <div style="max-width: 580px; margin: 0 auto; background: #ffffff; padding: 28px; border-radius: 16px; border: 1px solid #1e4d3b20;">
        <h2 style="color: #1e4d3b; margin-top: 0;">Academic Attendance Notice</h2>
        <p>Dear Parent / Guardian of <strong>{student.name}</strong>,</p>
        <p>This is an official attendance notice from the Academic Mentorship Department regarding your ward, <strong>{student.name}</strong> (USN: <code>{student.usn}</code>).</p>
        
        <div style="background-color: #f4f8f5; padding: 16px; border-radius: 12px; margin: 16px 0; font-size: 13px;">
          <p style="margin: 0 0 6px 0;"><strong>Date of Absence:</strong> {absence_date_str}</p>
          <p style="margin: 0 0 6px 0;"><strong>Subject(s) Missed:</strong> {sub_names}</p>
        </div>

        <p style="font-size: 13px; font-weight: bold;">Current Attendance Status (75% Minimum Required):</p>
        <div style="font-size: 13px; line-height: 1.6; white-space: pre-line; background: #ffffff; padding: 12px; border: 1px solid #e0e0e0; border-radius: 8px;">{stats_str}</div>

        <p style="font-size: 13px; line-height: 1.6; margin-top: 16px;">
          Our department contacted {student.name} earlier regarding this absence, but we have not received a response within 24 hours. 
          We kindly request you to speak with {student.name} to encourage consistent class attendance and ensure exam eligibility.
        </p>

        <div style="margin-top: 20px; padding: 14px; background-color: #e8f5e9; border-radius: 10px; font-size: 12px;">
          <strong>Mentor Contact Information:</strong><br>
          {mentor_contact}
        </div>

        <p style="font-size: 11px; color: #777; margin-top: 24px; text-align: center;">
          Attend Lens Academic System &bull; Official Parent Notification
        </p>
      </div>
    </body>
    </html>
    """

    return subject, text_body, html_body


def process_absence_followups(db: Session) -> Dict[str, Any]:
    """
    Main job processor:
    1. Syncs absent records for current date into AbsenceFollowUp table.
    2. Respects EMAIL_AUTOMATION_ENABLED and quiet hours window.
    3. Handles 2-step email sequence (student email -> 24h wait -> parent email).
    4. Enforces idempotency, retries (max 3), distress protection, and non-crashing execution.
    """
    # 1. Sync recent absent records
    try:
        today = datetime.now().date()
        create_or_sync_absence_followups(db, today)
        yesterday = today - timedelta(days=1)
        create_or_sync_absence_followups(db, yesterday)
    except Exception as sync_err:
        print(f"[FOLLOWUP SYNC ERROR] {sync_err}")

    if not settings.EMAIL_AUTOMATION_ENABLED:
        return {"status": "disabled", "processed": 0}

    if is_quiet_hours():
        print("[FOLLOWUP JOB] Quiet hours active (9 PM - 7 AM). Deferring email dispatch.")
        return {"status": "quiet_hours", "processed": 0}

    now = datetime.utcnow()
    wait_hours = settings.FOLLOWUP_WAIT_HOURS

    followups = db.query(AbsenceFollowUp).filter(
        AbsenceFollowUp.status.in_([
            FollowUpStatus.pending,
            FollowUpStatus.student_emailed,
            FollowUpStatus.failed
        ])
    ).all()

    processed_count = 0
    student_emailed_count = 0
    parent_emailed_count = 0
    responded_count = 0
    skipped_count = 0
    failed_count = 0

    for followup in followups:
        processed_count += 1

        # Check if max retries exceeded
        if followup.retry_count >= 3 and followup.status == FollowUpStatus.failed:
            skipped_count += 1
            continue

        # ALWAYS check for student response before any email
        if check_if_student_has_responded(db, followup):
            responded_count += 1
            continue

        student = db.query(Student).filter(Student.id == followup.student_id).first()
        if not student:
            followup.status = FollowUpStatus.failed
            followup.last_error = "Student record not found"
            db.commit()
            failed_count += 1
            continue

        # STEP 1: Student Email
        if followup.status == FollowUpStatus.pending or (followup.status == FollowUpStatus.failed and not followup.student_email_sent_at):
            if not student.email or not validate_email(student.email):
                print(f"[FOLLOWUP SKIP] Student #{student.id} ({student.name}) has no valid email.")
                followup.status = FollowUpStatus.failed
                followup.last_error = "Missing or invalid student email"
                db.commit()
                skipped_count += 1
                continue

            sub, text_b, html_b = generate_student_followup_email_text(db, followup)
            if not sub or not text_b:
                # OpenRouter call failed -> increment retry count, keep pending for next job run
                followup.retry_count += 1
                followup.last_error = "AI student email generation failed"
                if followup.retry_count >= 3:
                    followup.status = FollowUpStatus.failed
                db.commit()
                failed_count += 1
                continue

            sent_ok = send_email(student.email, sub, text_b, html_b)
            if sent_ok:
                followup.status = FollowUpStatus.student_emailed
                followup.student_email_sent_at = datetime.utcnow()
                followup.last_error = None
                db.commit()
                student_emailed_count += 1
            else:
                followup.retry_count += 1
                followup.last_error = f"Failed to send email to student {student.email}"
                if followup.retry_count >= 3:
                    followup.status = FollowUpStatus.failed
                db.commit()
                failed_count += 1

        # STEP 2 & 3: 24h Wait Check & Parent Email Escalation
        elif followup.status == FollowUpStatus.student_emailed or (followup.status == FollowUpStatus.failed and followup.student_email_sent_at):
            if not followup.student_email_sent_at:
                continue

            elapsed_hours = (now - followup.student_email_sent_at).total_seconds() / 3600.0
            if elapsed_hours >= wait_hours:
                # Re-verify student response before sending parent email
                if check_if_student_has_responded(db, followup):
                    responded_count += 1
                    continue

                # Safety check: distress/self-harm protection
                if has_distress_flag(db, followup.student_id):
                    print(f"[FOLLOWUP SAFETY] Student #{student.id} has active distress flag. Skipping parent email escalation.")
                    followup.status = FollowUpStatus.cancelled
                    followup.last_error = "Parent email skipped due to active distress flag"
                    db.commit()
                    skipped_count += 1
                    continue

                # Check parent email
                if not student.parent_email or not validate_email(student.parent_email):
                    print(f"[FOLLOWUP SKIP] Student #{student.id} ({student.name}) has no valid parent email.")
                    followup.status = FollowUpStatus.failed
                    followup.last_error = "Missing or invalid parent email"
                    db.commit()
                    skipped_count += 1
                    continue

                sub, text_b, html_b = generate_parent_followup_email_text(db, followup)
                if not sub or not text_b:
                    followup.retry_count += 1
                    followup.last_error = "Parent email content generation failed"
                    if followup.retry_count >= 3:
                        followup.status = FollowUpStatus.failed
                    db.commit()
                    failed_count += 1
                    continue

                sent_ok = send_email(student.parent_email, sub, text_b, html_b)
                if sent_ok:
                    followup.status = FollowUpStatus.parent_emailed
                    followup.parent_email_sent_at = datetime.utcnow()
                    followup.last_error = None
                    db.commit()
                    parent_emailed_count += 1
                else:
                    followup.retry_count += 1
                    followup.last_error = f"Failed to send email to parent {student.parent_email}"
                    if followup.retry_count >= 3:
                        followup.status = FollowUpStatus.failed
                    db.commit()
                    failed_count += 1

    return {
        "status": "success",
        "processed": processed_count,
        "student_emailed": student_emailed_count,
        "parent_emailed": parent_emailed_count,
        "responded": responded_count,
        "skipped": skipped_count,
        "failed": failed_count
    }


# ---------------------------------------------------------------- Immediate Backend Email Queueing Services

def build_student_absence_email_content(db: Session, student: Student, absence_date: date, subject_ids: List[int], teacher_name: Optional[str] = None) -> Tuple[str, str, str]:
    first_name = student.name.split()[0] if student.name else "Student"
    sub_names, stats_str = get_subject_names_and_pct(db, student, subject_ids)
    absence_date_str = absence_date.strftime("%A, %b %d, %Y")
    t_name = teacher_name or "your course instructor"
    counselling_url = settings.APP_BASE_URL.rstrip("/")

    subject = f"Absence recorded: {absence_date_str} | Attend Lens"

    text_body = (
        f"Dear {first_name},\n\n"
        f"An absence was recorded for you on {absence_date_str} for {sub_names} by teacher {t_name}.\n\n"
        f"Current Subject Attendance Status (vs 75% Cutoff):\n"
        f"{stats_str}\n\n"
        f"Please go through counselling within 24 hours.\n\n"
        f"Go to Counselling: {counselling_url}\n\n"
        f"If this absence was recorded by mistake, please reply to your mentor or college contact.\n\n"
        f"Warm regards,\n"
        f"Attend Lens"
    )

    html_body = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: Arial, sans-serif; background-color: #f4f8f5; padding: 20px; color: #143628;">
  <div style="max-width: 580px; margin: 0 auto; background: #ffffff; padding: 28px; border-radius: 16px; border: 1px solid #1e4d3b20;">
    <h2 style="color: #1e4d3b; margin-top: 0;">Absence Notification</h2>
    <p>Dear <strong>{first_name}</strong>,</p>
    <p>An absence was recorded for you on <strong>{absence_date_str}</strong> for <strong>{sub_names}</strong> by teacher <strong>{t_name}</strong>.</p>
    
    <div style="background-color: #f4f8f5; padding: 14px; border-radius: 10px; margin: 16px 0; font-size: 13px;">
      <p style="margin: 0 0 6px 0; font-weight: bold;">Current Subject Attendance Status (vs 75% Cutoff):</p>
      <div style="white-space: pre-line; line-height: 1.6;">{stats_str}</div>
    </div>

    <p style="font-size: 15px; margin: 20px 0;"><strong>Please go through counselling within 24 hours.</strong></p>

    <div style="text-align: center; margin: 24px 0;">
      <a href="{counselling_url}" style="display: inline-block; background-color: #1e4d3b; color: #ffffff; font-weight: bold; font-size: 14px; padding: 12px 28px; text-decoration: none; border-radius: 8px;">
        Go to Counselling
      </a>
    </div>

    <p style="font-size: 12px; color: #555; margin-top: 20px;">
      If this absence was recorded by mistake, please reply to your mentor or college contact.
    </p>

    <p style="font-size: 13px; color: #143628; margin-top: 24px;">
      Warm regards,<br>
      <strong>Attend Lens</strong>
    </p>
  </div>
</body>
</html>"""

    return subject, text_body, html_body


def build_parent_absence_email_content(db: Session, student: Student, absence_date: date, subject_ids: List[int], teacher_name: Optional[str] = None) -> Tuple[str, str, str]:
    sub_names, stats_str = get_subject_names_and_pct(db, student, subject_ids)
    absence_date_str = absence_date.strftime("%A, %b %d, %Y")

    mentor_contact = "Academic Mentorship Department (Email: mentor@attendlens.edu)"
    if student.classroom and student.classroom.mentor and student.classroom.mentor.user:
        u = student.classroom.mentor.user
        mentor_contact = f"{u.name} (Email: {u.email or 'mentor@attendlens.edu'})"

    subject = f"Absence notice: {student.name} - {absence_date_str} | Attend Lens"

    text_body = (
        f"Dear Parent/Guardian of {student.name},\n\n"
        f"This is an official notification that your ward, {student.name} (USN: {student.usn}), was marked absent on {absence_date_str} for {sub_names}.\n\n"
        f"Current Subject Attendance Status (vs 75% Cutoff):\n"
        f"{stats_str}\n\n"
        f"Please go through counselling within 24 hours.\n\n"
        f"Please encourage {student.name} to complete their counselling session within 24 hours.\n\n"
        f"Mentor Contact Information:\n"
        f"{mentor_contact}\n\n"
        f"If this absence was recorded by mistake, please contact your ward's mentor.\n"
        f"Notice: Only attendance facts are included in this communication.\n\n"
        f"Sincerely,\n"
        f"Attend Lens Academic System"
    )

    html_body = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: Arial, sans-serif; background-color: #f8faf9; padding: 20px; color: #143628;">
  <div style="max-width: 580px; margin: 0 auto; background: #ffffff; padding: 28px; border-radius: 16px; border: 1px solid #1e4d3b20;">
    <h2 style="color: #1e4d3b; margin-top: 0;">Academic Absence Notice</h2>
    <p>Dear Parent / Guardian of <strong>{student.name}</strong>,</p>
    <p>This is an official notification that your ward, <strong>{student.name}</strong> (USN: <code>{student.usn}</code>), was marked absent on <strong>{absence_date_str}</strong> for <strong>{sub_names}</strong>.</p>
    
    <div style="background-color: #f4f8f5; padding: 14px; border-radius: 10px; margin: 16px 0; font-size: 13px;">
      <p style="margin: 0 0 6px 0; font-weight: bold;">Current Subject Attendance Status (vs 75% Cutoff):</p>
      <div style="white-space: pre-line; line-height: 1.6;">{stats_str}</div>
    </div>

    <p style="font-size: 15px; margin: 20px 0;"><strong>Please go through counselling within 24 hours.</strong></p>

    <p style="font-size: 13px; line-height: 1.6;">
      Please encourage <strong>{student.name}</strong> to complete their counselling session within 24 hours to ensure academic progress and attendance compliance.
    </p>

    <div style="margin-top: 20px; padding: 14px; background-color: #e8f5e9; border-radius: 10px; font-size: 12px;">
      <strong>Mentor Contact Information:</strong><br>
      {mentor_contact}
    </div>

    <p style="font-size: 11px; color: #777; margin-top: 24px; text-align: center;">
      If this absence was recorded by mistake, please contact your ward's mentor.<br>
      Notice: Only attendance facts are included in this communication.
    </p>

    <p style="font-size: 12px; color: #143628; margin-top: 20px;">
      Sincerely,<br>
      <strong>Attend Lens Academic System</strong>
    </p>
  </div>
</body>
</html>"""

    return subject, text_body, html_body


def queue_immediate_absence_emails(
    db: Session,
    teacher_user_id: int,
    subject_id: int,
    absence_date: date,
    absent_student_ids: List[int]
) -> int:
    """
    Enqueues immediate absence email notifications for student and parent when a teacher saves attendance.
    Idempotent: Groups multiple absent subjects on the same date into a single queue item per recipient.
    Does not duplicate previously sent or queued notifications for the exact same subject.
    """
    if not absent_student_ids:
        return 0

    teacher_user = db.query(User).filter(User.id == teacher_user_id).first()
    teacher_name = teacher_user.name if teacher_user else "Teacher"

    count = 0
    for student_id in set(absent_student_ids):
        student = db.query(Student).filter(Student.id == student_id).first()
        if not student:
            continue

        for r_type in [QueueRecipientType.student, QueueRecipientType.parent]:
            rec_email = student.email if r_type == QueueRecipientType.student else student.parent_email

            # Check if an existing queue item exists for (student_id, r_type, absence_date)
            existing = db.query(EmailQueue).filter(
                EmailQueue.student_id == student_id,
                EmailQueue.recipient_type == r_type,
                EmailQueue.absence_date == absence_date
            ).first()

            if existing:
                current_subs = existing.subject_ids or []
                if subject_id not in current_subs:
                    current_subs.append(subject_id)
                    existing.subject_ids = current_subs
                    # If previously finished or failed, reset to pending for the newly marked subject
                    if existing.status in [QueueStatus.sent, QueueStatus.failed]:
                        existing.status = QueueStatus.pending
                        existing.retry_count = 0
                        existing.last_error = None
                    count += 1
            else:
                q_item = EmailQueue(
                    student_id=student_id,
                    recipient_type=r_type,
                    recipient_email=rec_email,
                    absence_date=absence_date,
                    subject_ids=[subject_id],
                    teacher_name=teacher_name,
                    status=QueueStatus.pending
                )
                db.add(q_item)
                count += 1

    db.commit()
    return count


def process_email_queue(db: Session) -> Dict[str, Any]:
    """
    Processes pending and retriable failed items in the EmailQueue.
    Sends emails via Gmail/SMTP with sequential delays to respect Gmail limits.
    Enforces student/parent error independence, distress flag safety, and max 3 retries.
    """
    if not settings.EMAIL_AUTOMATION_ENABLED:
        return {"status": "disabled", "processed": 0}

    pending_items = db.query(EmailQueue).filter(
        EmailQueue.status.in_([QueueStatus.pending, QueueStatus.failed]),
        EmailQueue.retry_count < 3
    ).all()

    processed = 0
    sent_count = 0
    skipped_count = 0
    failed_count = 0

    for item in pending_items:
        processed += 1
        student = db.query(Student).filter(Student.id == item.student_id).first()

        if not student:
            item.status = QueueStatus.failed
            item.last_error = "Student record not found"
            db.commit()
            failed_count += 1
            continue

        # SAFETY CHECK: If parent email & student has distress flag -> skip parent email
        if item.recipient_type == QueueRecipientType.parent and has_distress_flag(db, item.student_id):
            print(f"[SAFETY SKIP] Student #{student.id} ({student.name}) has distress flag. Skipping parent email.")
            item.status = QueueStatus.skipped
            item.last_error = "Skipped due to active distress flag"
            db.commit()
            skipped_count += 1
            continue

        # VALIDATION: Check recipient email
        target_email = item.recipient_email or (student.email if item.recipient_type == QueueRecipientType.student else student.parent_email)
        if not target_email or not validate_email(target_email):
            print(f"[QUEUE SKIP] Student #{student.id} ({student.name}) has missing or invalid {item.recipient_type.value} email: '{target_email}'")
            item.status = QueueStatus.skipped
            item.last_error = f"Missing or invalid {item.recipient_type.value} email address"
            db.commit()
            skipped_count += 1
            continue

        # BUILD EMAIL CONTENT
        if item.recipient_type == QueueRecipientType.student:
            sub, text_b, html_b = build_student_absence_email_content(db, student, item.absence_date, item.subject_ids or [], item.teacher_name)
        else:
            sub, text_b, html_b = build_parent_absence_email_content(db, student, item.absence_date, item.subject_ids or [], item.teacher_name)

        # SEND EMAIL
        ok = send_email(target_email, sub, text_b, html_b)

        if ok:
            item.status = QueueStatus.sent
            item.sent_at = datetime.utcnow()
            item.last_error = None
            db.commit()
            sent_count += 1
        else:
            item.retry_count += 1
            item.last_error = f"SMTP send failure to {target_email}"
            if item.retry_count >= 3:
                item.status = QueueStatus.failed
            db.commit()
            failed_count += 1

        # Short sequential delay to avoid hitting rate limits
        pytime.sleep(0.2)

    return {
        "status": "success",
        "processed": processed,
        "sent": sent_count,
        "skipped": skipped_count,
        "failed": failed_count
    }

