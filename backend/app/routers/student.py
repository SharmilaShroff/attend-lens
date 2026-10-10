import pandas as pd
from datetime import datetime, date, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.models import (
    User, Student, Subject, Attendance, AttendanceStatus, AbsenceReason,
    ReasonStatus, CounsellingCase, CounsellingMessage
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
