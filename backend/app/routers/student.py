import pandas as pd
from datetime import datetime, date, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.models import (
    User, Student, Subject, Attendance, AttendanceStatus, AbsenceReason,
    ReasonStatus, CounsellingCase, CounsellingMessage, Alert
)
from app.schemas.all_schemas import (
    SubjectAttendanceSummary, AbsenceReasonCreate, AbsenceReasonOut,
    CounsellingCaseOut
)
from app.services.analytics import calculate_classes_needed, predict_student_drop_risk
from app.config import get_settings

settings = get_settings()

router = APIRouter(prefix="/student", tags=["student"])


def require_student(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Student:
    if user.role != "student":
        # Allow mentor/teacher viewing demo student data if requested
        s = db.query(Student).first()
        if s:
            return s
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Student access required")
    student = db.query(Student).filter(Student.user_id == user.id).first()
    if not student:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Student profile not found")
    return student


@router.get("/dashboard-data")
def get_student_dashboard(student: Student = Depends(require_student), db: Session = Depends(get_db)):
    subjects = db.query(Subject).filter(Subject.class_id == student.class_id).all()

    # If class has 0 subjects or only 1 single 'General Subject', expand to 5 distinct core subjects
    if not subjects or (len(subjects) == 1 and subjects[0].name == "General Subject"):
        old_records = []
        if subjects and len(subjects) == 1 and subjects[0].name == "General Subject":
            gen_sub = subjects[0]
            old_records = db.query(Attendance).filter(Attendance.subject_id == gen_sub.id).all()
            db.delete(gen_sub)
            db.commit()

        default_subjects = [
            ("Database Management Systems", "CS601"),
            ("Machine Learning", "CS602"),
            ("Computer Networks", "CS603"),
            ("Web Technologies", "CS604"),
            ("Software Engineering", "CS605")
        ]
        new_subjects = []
        for name, code in default_subjects:
            sub = Subject(class_id=student.class_id, name=name, code=code)
            db.add(sub)
            db.commit()
            db.refresh(sub)
            new_subjects.append(sub)

        # Distribute existing attendance records across the 5 distinct subjects
        if old_records and new_subjects:
            for idx, rec in enumerate(old_records):
                rec.subject_id = new_subjects[idx % len(new_subjects)].id
            db.commit()

        subjects = new_subjects

    records = db.query(Attendance).filter(Attendance.student_id == student.id).all()

    total_classes = len(records)
    total_attended = sum(1 for r in records if r.status == AttendanceStatus.present)
    overall_pct = (total_attended / total_classes * 100.0) if total_classes > 0 else 100.0

    # Subject-wise breakdown for overall bar chart

    subject_summaries = []
    for s in subjects:
        sub_recs = [r for r in records if r.subject_id == s.id]
        sub_tot = len(sub_recs)
        sub_att = sum(1 for r in sub_recs if r.status == AttendanceStatus.present)
        sub_pct = (sub_att / sub_tot * 100.0) if sub_tot > 0 else 100.0

        calc = calculate_classes_needed(sub_att, sub_tot, settings.ATTENDANCE_THRESHOLD)

        # Monthly line graph data
        monthly_trend = []
        if sub_recs:
            df = pd.DataFrame([{
                'date': r.date,
                'is_present': 1 if r.status == AttendanceStatus.present else 0
            } for r in sub_recs])
            df['month'] = pd.to_datetime(df['date']).dt.strftime('%b %Y')
            grouped = df.groupby('month', sort=False)
            for m_name, grp in grouped:
                m_pct = (grp['is_present'].sum() / len(grp)) * 100.0
                monthly_trend.append({"month": m_name, "percentage": round(m_pct, 1)})

        subject_summaries.append({
            "subject_id": s.id,
            "subject_name": s.name,
            "subject_code": s.code,
            "attended": sub_att,
            "total": sub_tot,
            "percentage": round(sub_pct, 1),
            "classes_needed": calc["classes_needed"],
            "safe_misses": calc["safe_misses"],
            "monthly_trend": monthly_trend
        })

    # Weekly Improvement Trend calculation
    trend_arrow = "neutral"
    weekly_pct_change = 0.0
    if records:
        df_all = pd.DataFrame([{
            'date': pd.to_datetime(r.date),
            'is_present': 1 if r.status == AttendanceStatus.present else 0
        } for r in records]).sort_values('date')

        max_d = df_all['date'].max()
        this_week = df_all[df_all['date'] > (max_d - pd.Timedelta(days=7))]
        last_week = df_all[(df_all['date'] <= (max_d - pd.Timedelta(days=7))) & (df_all['date'] > (max_d - pd.Timedelta(days=14)))]

        this_pct = (this_week['is_present'].mean() * 100.0) if len(this_week) > 0 else overall_pct
        last_pct = (last_week['is_present'].mean() * 100.0) if len(last_week) > 0 else overall_pct

        weekly_pct_change = round(this_pct - last_pct, 1)
        if weekly_pct_change > 1.5:
            trend_arrow = "up"
        elif weekly_pct_change < -1.5:
            trend_arrow = "down"

    prob_drop = predict_student_drop_risk(db, student.id)

    return {
        "student": {
            "id": student.id,
            "name": student.name,
            "usn": student.usn,
            "overall_pct": round(overall_pct, 1),
            "threshold": settings.ATTENDANCE_THRESHOLD,
            "predicted_risk_prob": prob_drop,
            "trend_arrow": trend_arrow,
            "weekly_change": weekly_pct_change
        },
        "subjects": subject_summaries
    }


# --- Absence Reasons Submission ---
@router.post("/absence-reasons", response_model=AbsenceReasonOut)
def submit_absence_reason(
    body: AbsenceReasonCreate,
    student: Student = Depends(require_student),
    db: Session = Depends(get_db)
):
    reason = AbsenceReason(
        student_id=student.id,
        subject_id=body.subject_id,
        date=body.date,
        category=body.category,
        reason=body.reason,
        proof_path=body.proof_path,
        status=ReasonStatus.pending
    )
    db.add(reason)
    db.commit()
    db.refresh(reason)
    
    try:
        from app.services.counselling import create_or_get_counselling_case, generate_counselling_reply, generate_and_save_counselling_summary
        from app.models.models import Alert, RiskLevel, CounsellingMessage
        
        recent_case = db.query(CounsellingCase).filter(
            CounsellingCase.student_id == student.id
        ).order_by(CounsellingCase.created_at.desc()).first()

        if not recent_case:
            alert = Alert(
                student_id=student.id,
                type="absence_reason_submission",
                risk_score=0.6,
                level=RiskLevel.medium,
                explanation={"reasons": [f"Absence on {reason.date}: {reason.reason}"]}
            )
            db.add(alert)
            db.commit()
            db.refresh(alert)
            recent_case = create_or_get_counselling_case(db, alert)
        else:
            # Add message and AI response to the active thread
            user_msg = CounsellingMessage(
                case_id=recent_case.id,
                sender="student",
                channel="app",
                body=f"Submitted Absence Reason for {reason.date} ({reason.category}): {reason.reason}"
            )
            db.add(user_msg)
            
            ai_body, pred = generate_counselling_reply(student, recent_case, reason.reason, db=db)
            ai_msg = CounsellingMessage(
                case_id=recent_case.id,
                sender="ai",
                channel="app",
                body=ai_body
            )
            db.add(ai_msg)
            db.commit()

            # Generate/update Counselling Summary in mentor's Remarks
            generate_and_save_counselling_summary(db, recent_case.id)
    except Exception as e:
        print(f"[Counselling Trigger Error] {e}")

    return AbsenceReasonOut.model_validate(reason)


@router.get("/absence-reasons", response_model=list[AbsenceReasonOut])
def list_absence_reasons(student: Student = Depends(require_student), db: Session = Depends(get_db)):
    reasons = db.query(AbsenceReason).filter(AbsenceReason.student_id == student.id).order_by(AbsenceReason.created_at.desc()).all()
    res = []
    for r in reasons:
        out = AbsenceReasonOut.model_validate(r)
        if r.subject_id:
            s = db.query(Subject).filter(Subject.id == r.subject_id).first()
            out.subject_name = s.name if s else None
        res.append(out)
    return res


# --- AI Counselling Inbox ---
@router.get("/counselling-cases", response_model=list[CounsellingCaseOut])
def get_student_counselling_cases(student: Student = Depends(require_student), db: Session = Depends(get_db)):
    cases = db.query(CounsellingCase).filter(CounsellingCase.student_id == student.id).order_by(CounsellingCase.created_at.desc()).all()
    res = []

    for c in cases:
        out = CounsellingCaseOut.model_validate(c)
        out.student_name = student.name
        res.append(out)
    return res


# --- Per-Subject Detailed Attendance Records ---
@router.get("/subjects/{subject_id}/records")
def get_student_subject_records(
    subject_id: int,
    student: Student = Depends(require_student),
    db: Session = Depends(get_db)
):
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    records = (
        db.query(Attendance)
        .filter(Attendance.student_id == student.id, Attendance.subject_id == subject_id)
        .order_by(Attendance.date.desc(), Attendance.period.desc())
        .all()
    )

    total = len(records)
    present_records = []
    absent_records = []

    for r in records:
        dt = datetime.strptime(r.date, "%Y-%m-%d") if isinstance(r.date, str) else r.date
        status_val = r.status.value if hasattr(r.status, "value") else str(r.status)
        item = {
            "id": r.id,
            "date": r.date,
            "day_of_week": dt.strftime("%A"),
            "formatted_date": dt.strftime("%b %d, %Y"),
            "period": r.period,
            "status": status_val
        }
        if status_val == "present":
            present_records.append(item)
        else:
            absent_records.append(item)

    attended = len(present_records)
    pct = round((attended / total * 100.0), 1) if total > 0 else 100.0

    return {
        "subject": {
            "id": subject.id,
            "name": subject.name,
            "code": subject.code,
            "overall_pct": pct,
            "total_classes": total,
            "attended_classes": attended,
            "absent_classes": len(absent_records)
        },
        "present_classes": present_records,
        "absent_classes": absent_records
    }

