"""
n8n Webhook Integration Service for Attend Lens.
Sends attendance-absent payloads to an n8n workflow that dispatches
Gmail notifications to students and parents.

De-duplication: Uses `n8n_notification_log` table keyed by
(subject_id, student_id, date, period) to avoid duplicate emails.
"""
import json
import urllib.request
from datetime import date as date_type, datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.models import (
    Student, Subject, User, N8nNotificationLog
)

settings = get_settings()

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def notify_absentees_via_n8n(
    db: Session,
    teacher_user_id: int,
    subject_id: int,
    attendance_date: date_type,
    period: int,
    absent_student_ids: List[int],
) -> Dict[str, Any]:
    """
    Called asynchronously (BackgroundTasks) after attendance is saved.
    Builds the payload, filters out already-notified students, posts
    to the n8n webhook, and logs sent notifications.

    Returns a summary dict (for logging, not sent back to the teacher).
    """
    webhook_url = settings.N8N_ABSENCE_WEBHOOK_URL.strip()
    webhook_secret = settings.N8N_WEBHOOK_SECRET.strip()

    if not webhook_url:
        return {"status": "skipped", "reason": "N8N_ABSENCE_WEBHOOK_URL not configured"}

    if not absent_student_ids:
        return {"status": "skipped", "reason": "no absent students"}

    # --- Resolve teacher info ---
    teacher_user = db.query(User).filter(User.id == teacher_user_id).first()
    teacher_name = teacher_user.name if teacher_user else "Teacher"

    # --- Resolve subject info ---
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        return {"status": "error", "reason": f"subject_id {subject_id} not found"}

    # --- De-duplicate: skip students already notified for this session ---
    new_absent_ids = _filter_already_notified(
        db, subject_id, attendance_date, period, absent_student_ids
    )
    if not new_absent_ids:
        return {"status": "skipped", "reason": "all absent students already notified"}

    # --- Build absentees list with minimal PII ---
    absentees = []
    for sid in new_absent_ids:
        student = db.query(Student).filter(Student.id == sid).first()
        if not student:
            continue
        absentees.append({
            "student_id": student.id,
            "name": student.name,
            "usn": student.usn,
            "student_email": student.email or "",
            "parent_email": student.parent_email or "",
            "parent_name": ""  # Not stored yet; n8n template handles gracefully
        })

    if not absentees:
        return {"status": "skipped", "reason": "no valid students found"}

    # --- Build session_id ---
    session_id = f"{subject_id}-{attendance_date.isoformat()}-P{period}"

    payload = {
        "session_id": session_id,
        "date": attendance_date.isoformat(),
        "period": str(period),
        "subject": {"code": subject.code, "name": subject.name},
        "teacher": {"id": str(teacher_user_id), "name": teacher_name},
        "absentees": absentees,
    }

    # --- POST to n8n with retry (max 2 attempts) ---
    result = _post_to_n8n(webhook_url, webhook_secret, payload, max_retries=2, timeout=5)

    # --- Log successful notifications ---
    if result.get("success"):
        _log_notifications(db, subject_id, attendance_date, period, new_absent_ids)

    return result


# ---------------------------------------------------------------------------
# De-duplication helpers
# ---------------------------------------------------------------------------

def _filter_already_notified(
    db: Session,
    subject_id: int,
    attendance_date: date_type,
    period: int,
    student_ids: List[int],
) -> List[int]:
    """Return only student_ids that have NOT been notified for this session."""
    already = db.query(N8nNotificationLog.student_id).filter(
        N8nNotificationLog.subject_id == subject_id,
        N8nNotificationLog.date == attendance_date,
        N8nNotificationLog.period == period,
        N8nNotificationLog.student_id.in_(student_ids),
    ).all()
    already_set = {row[0] for row in already}
    return [sid for sid in student_ids if sid not in already_set]


def _log_notifications(
    db: Session,
    subject_id: int,
    attendance_date: date_type,
    period: int,
    student_ids: List[int],
) -> None:
    """Insert rows into n8n_notification_log so we don't re-notify."""
    for sid in student_ids:
        log = N8nNotificationLog(
            student_id=sid,
            subject_id=subject_id,
            date=attendance_date,
            period=period,
        )
        db.add(log)
    try:
        db.commit()
    except Exception:
        db.rollback()


# ---------------------------------------------------------------------------
# HTTP helper
# ---------------------------------------------------------------------------

def _post_to_n8n(
    url: str,
    secret: str,
    payload: dict,
    max_retries: int = 2,
    timeout: int = 5,
) -> Dict[str, Any]:
    """POST JSON to the n8n webhook. Retries on failure up to max_retries."""
    data = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "AttendLens-Backend",
    }
    if secret:
        headers["X-Webhook-Secret"] = secret

    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            req = urllib.request.Request(url, data=data, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                status_code = resp.getcode()
                body = resp.read().decode("utf-8", errors="replace")
                if status_code in (200, 201, 202):
                    print(f"[N8N ABSENT WEBHOOK] OK (attempt {attempt}) -> HTTP {status_code}")
                    try:
                        resp_data = json.loads(body)
                    except Exception:
                        resp_data = {"raw": body}
                    return {"success": True, "status_code": status_code, "response": resp_data}
                else:
                    last_error = f"HTTP {status_code}: {body[:200]}"
        except Exception as e:
            last_error = str(e)
            print(f"[N8N ABSENT WEBHOOK] Attempt {attempt} failed: {last_error}")

    print(f"[N8N ABSENT WEBHOOK] All {max_retries} attempts failed: {last_error}")
    return {"success": False, "error": last_error}
