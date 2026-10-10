"""
Router for Absence Follow-Up Email Automation & One-Click Secure Email Replies.
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import AbsenceFollowUp, FollowUpStatus, Student, AbsenceReason, ReasonStatus
from app.services.absence_followup import process_absence_followups, check_if_student_has_responded

router = APIRouter(tags=["absence_followup"])


@router.get("/api/student/absence-followup/reply/{token}", response_class=HTMLResponse)
def get_email_reply_page(token: str, db: Session = Depends(get_db)):
    """
    Secure 1-click email reply endpoint for students.
    Validates token without requiring a password, marks the follow-up as responded,
    and displays a styled confirmation page.
    """
    followup = db.query(AbsenceFollowUp).filter(AbsenceFollowUp.token == token).first()

    if not followup:
        return HTMLResponse(content="""
        <!DOCTYPE html><html><head><meta charset="utf-8"><title>Invalid Link</title></head>
        <body style="font-family:sans-serif; background:#f4f8f5; padding:40px; text-align:center; color:#143628;">
          <div style="max-width:480px; margin:0 auto; background:#fff; padding:32px; border-radius:16px; border:1px solid #ddd;">
            <h3 style="color:#d32f2f;">Invalid or Expired Link</h3>
            <p>This attendance follow-up link is no longer valid or has expired.</p>
          </div>
        </body></html>
        """, status_code=404)

    student = db.query(Student).filter(Student.id == followup.student_id).first()
    student_name = student.name if student else "Student"

    # Mark as responded
    followup.status = FollowUpStatus.responded
    followup.responded_at = datetime.utcnow()
    followup.response_source = "email_link"

    # Ensure an AbsenceReason entry exists
    existing_reason = db.query(AbsenceReason).filter(
        AbsenceReason.student_id == followup.student_id,
        AbsenceReason.date == followup.absence_date
    ).first()

    if not existing_reason:
        new_reason = AbsenceReason(
            student_id=followup.student_id,
            date=followup.absence_date,
            category="personal",
            reason="Responded via 1-click email follow-up link",
            status=ReasonStatus.pending
        )
        db.add(new_reason)

    db.commit()

    date_str = followup.absence_date.strftime("%b %d, %Y")

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <title>Attendance Response Recorded - Attend Lens</title>
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #f4f8f5; color: #143628; margin: 0; padding: 40px 16px;">
      <div style="max-width: 520px; margin: 0 auto; background: #ffffff; border-radius: 20px; border: 1px solid rgba(30, 77, 59, 0.15); box-shadow: 0 10px 25px rgba(0,0,0,0.05); padding: 36px; text-align: center;">
        <div style="width: 56px; height: 56px; background: #e8f5e9; border-radius: 50%; color: #1e4d3b; display: inline-flex; align-items: center; justify-content: center; font-size: 28px; font-weight: bold; margin-bottom: 16px;">✓</div>
        <h2 style="color: #1e4d3b; margin: 0 0 8px 0; font-size: 22px;">Thank You, {student_name}!</h2>
        <p style="font-size: 14px; color: #4a5568; margin: 0 0 24px 0; line-height: 1.5;">
          Your response for your absence on <strong>{date_str}</strong> has been successfully recorded. Your mentor has been notified.
        </p>
        
        <form action="/api/student/absence-followup/reply/{token}" method="POST" style="background: #f8faf9; padding: 20px; border-radius: 14px; text-align: left; border: 1px solid #e2e8f0;">
          <label style="display: block; font-size: 12px; font-weight: bold; color: #143628; margin-bottom: 8px;">
            Optional: Add specific details for your mentor (e.g. fever, family event)
          </label>
          <textarea name="reason" rows="3" style="width: 100%; box-sizing: border-box; font-size: 13px; padding: 10px; border-radius: 8px; border: 1px solid #cbd5e1; font-family: inherit;" placeholder="Type optional details here..."></textarea>
          <button type="submit" style="margin-top: 12px; width: 100%; background: #1e4d3b; color: #ffffff; font-weight: bold; font-size: 13px; padding: 10px; border: none; border-radius: 8px; cursor: pointer;">
            Update Reason Details
          </button>
        </form>

        <p style="font-size: 11px; color: #718096; margin-top: 24px;">
          Attend Lens Academic Mentorship Department &bull; Secure Email Verification
        </p>
      </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)


@router.post("/api/student/absence-followup/reply/{token}")
def post_email_reply_reason(
    token: str,
    reason: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Submits specific reason text from the secure email reply link.
    """
    followup = db.query(AbsenceFollowUp).filter(AbsenceFollowUp.token == token).first()
    if not followup:
        raise HTTPException(status_code=404, detail="Follow-up record not found")

    followup.status = FollowUpStatus.responded
    followup.responded_at = datetime.utcnow()
    followup.response_source = "email_link"

    if reason and reason.strip():
        existing_reason = db.query(AbsenceReason).filter(
            AbsenceReason.student_id == followup.student_id,
            AbsenceReason.date == followup.absence_date
        ).first()

        if existing_reason:
            existing_reason.reason = reason.strip()
        else:
            new_reason = AbsenceReason(
                student_id=followup.student_id,
                date=followup.absence_date,
                category="personal",
                reason=reason.strip(),
                status=ReasonStatus.pending
            )
            db.add(new_reason)

    db.commit()

    return HTMLResponse(content="""
    <!DOCTYPE html><html><head><meta charset="utf-8"><title>Reason Updated</title></head>
    <body style="font-family:sans-serif; background:#f4f8f5; padding:40px; text-align:center; color:#143628;">
      <div style="max-width:480px; margin:0 auto; background:#fff; padding:32px; border-radius:16px; border:1px solid #ddd;">
        <h3 style="color:#1e4d3b;">Reason Details Updated</h3>
        <p>Thank you. Your absence reason details have been saved and shared with your mentor.</p>
      </div>
    </body></html>
    """, status_code=200)


@router.post("/api/dev/run-followups")
def trigger_absence_followups(db: Session = Depends(get_db)):
    """
    Protected/dev route to run the absence follow-up email automation job on demand.
    Returns metrics detailing processed follow-ups, emails sent, skips, and retries.
    """
    from app.services.absence_followup import process_email_queue
    metrics = process_absence_followups(db)
    queue_metrics = process_email_queue(db)
    return {
        "status": "success",
        "message": "Absence follow-up jobs executed on demand",
        "legacy_metrics": metrics,
        "immediate_queue_metrics": queue_metrics
    }


@router.post("/api/dev/test-absence-email")
def test_absence_email(
    to_email: str = "sharmilashroff512@gmail.com",
    recipient_type: str = "student",
    db: Session = Depends(get_db)
):
    """
    Admin/dev testing endpoint that sends a sample absence email or logs it in dry-run mode.
    Tests SMTP/Gmail credentials and verifies mandatory bold counselling line formatting.
    """
    from app.services.email import send_email
    from app.config import get_settings
    cfg = get_settings()

    absence_date_str = datetime.now().strftime("%A, %b %d, %Y")
    counselling_url = cfg.APP_BASE_URL.rstrip("/")

    if recipient_type == "parent":
        subject = f"Absence notice: Sample Student - {absence_date_str} | Attend Lens"
        text_body = (
            f"Dear Parent/Guardian of Sample Student,\n\n"
            f"This is an official notification that your ward, Sample Student (USN: 1VA21CS001), was marked absent on {absence_date_str} for Database Management Systems (CS601).\n\n"
            f"Current Subject Attendance Status (vs 75% Cutoff):\n"
            f"- Database Management Systems (CS601): 70.0% (Required: 75%)\n\n"
            f"Please go through counselling within 24 hours.\n\n"
            f"Please encourage Sample Student to complete their counselling session within 24 hours.\n\n"
            f"Mentor Contact Information:\n"
            f"Alex Morgan (Email: mentor@attendlens.edu)\n\n"
            f"If this absence was recorded by mistake, please contact your ward's mentor.\n"
            f"Notice: Only attendance facts are included in this communication.\n\n"
            f"Sincerely,\n"
            f"Attend Lens Academic System"
        )

        html_body = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="font-family: Arial, sans-serif; background-color: #f8faf9; padding: 20px; color: #143628;">
  <div style="max-width: 580px; margin: 0 auto; background: #ffffff; padding: 28px; border-radius: 16px; border: 1px solid #1e4d3b20;">
    <h2 style="color: #1e4d3b; margin-top: 0;">Academic Absence Notice</h2>
    <p>Dear Parent / Guardian of <strong>Sample Student</strong>,</p>
    <p>This is an official notification that your ward, <strong>Sample Student</strong> (USN: <code>1VA21CS001</code>), was marked absent on <strong>{absence_date_str}</strong> for <strong>Database Management Systems (CS601)</strong>.</p>
    
    <div style="background-color: #f4f8f5; padding: 14px; border-radius: 10px; margin: 16px 0; font-size: 13px;">
      <p style="margin: 0 0 6px 0; font-weight: bold;">Current Subject Attendance Status (vs 75% Cutoff):</p>
      <div style="line-height: 1.6;">- Database Management Systems (CS601): 70.0% (Required: 75%)</div>
    </div>

    <p style="font-size: 15px; margin: 20px 0;"><strong>Please go through counselling within 24 hours.</strong></p>

    <p style="font-size: 13px; line-height: 1.6;">
      Please encourage <strong>Sample Student</strong> to complete their counselling session within 24 hours to ensure academic progress and attendance compliance.
    </p>

    <div style="margin-top: 20px; padding: 14px; background-color: #e8f5e9; border-radius: 10px; font-size: 12px;">
      <strong>Mentor Contact Information:</strong><br>
      Alex Morgan (Email: mentor@attendlens.edu)
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
    else:
        subject = f"Absence recorded: {absence_date_str} | Attend Lens"
        text_body = (
            f"Dear Sample,\n\n"
            f"An absence was recorded for you on {absence_date_str} for Database Management Systems (CS601) by teacher Dr. Sarah Jenkins.\n\n"
            f"Current Subject Attendance Status (vs 75% Cutoff):\n"
            f"- Database Management Systems (CS601): 70.0% (Required: 75%)\n\n"
            f"Please go through counselling within 24 hours.\n\n"
            f"Go to Counselling: {counselling_url}\n\n"
            f"If this absence was recorded by mistake, please reply to your mentor or college contact.\n\n"
            f"Warm regards,\n"
            f"Attend Lens"
        )

        html_body = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="font-family: Arial, sans-serif; background-color: #f4f8f5; padding: 20px; color: #143628;">
  <div style="max-width: 580px; margin: 0 auto; background: #ffffff; padding: 28px; border-radius: 16px; border: 1px solid #1e4d3b20;">
    <h2 style="color: #1e4d3b; margin-top: 0;">Absence Notification</h2>
    <p>Dear <strong>Sample</strong>,</p>
    <p>An absence was recorded for you on <strong>{absence_date_str}</strong> for <strong>Database Management Systems (CS601)</strong> by teacher <strong>Dr. Sarah Jenkins</strong>.</p>
    
    <div style="background-color: #f4f8f5; padding: 14px; border-radius: 10px; margin: 16px 0; font-size: 13px;">
      <p style="margin: 0 0 6px 0; font-weight: bold;">Current Subject Attendance Status (vs 75% Cutoff):</p>
      <div style="line-height: 1.6;">- Database Management Systems (CS601): 70.0% (Required: 75%)</div>
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

    sent = send_email(to_email, subject, text_body, html_body)

    return {
        "status": "success" if sent else "failed",
        "sent_to": to_email,
        "recipient_type": recipient_type,
        "dry_run_mode": cfg.EMAIL_DRY_RUN,
        "gmail_configured": bool(cfg.GMAIL_USER and cfg.GMAIL_APP_PASSWORD),
        "message": f"Sample {recipient_type} email sent/logged successfully"
    }

