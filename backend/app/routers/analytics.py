import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.models import User, Student, Alert, Subject, Attendance, AttendanceStatus, ClassRoom
from app.schemas.all_schemas import RunAnalyticsResponse, RiskPredictionOut
from app.services.analytics import (
    run_analytics_for_student, predict_student_drop_risk, run_openrouter_analysis_for_class, calculate_classes_needed,
    get_student_8_points_analysis
)

from app.config import get_settings

settings = get_settings()

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.post("/run", response_model=RunAnalyticsResponse)
def run_analytics_manual(class_id: int | None = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(Student)
    if class_id:
        query = query.filter(Student.class_id == class_id)
    students = query.all()

    total_alerts = 0
    for s in students:
        alerts = run_analytics_for_student(db, s.id)
        total_alerts += len(alerts)

    return RunAnalyticsResponse(
        status="success",
        processed_students=len(students),
        raised_alerts=total_alerts
    )


@router.post("/run-openrouter")
def run_openrouter_manual(class_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return run_openrouter_analysis_for_class(db, class_id)


@router.get("/predictions", response_model=list[RiskPredictionOut])
def get_risk_predictions(class_id: int | None = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(Student)
    if class_id:
        query = query.filter(Student.class_id == class_id)
    students = query.all()

    res = []
    for s in students:
        prob = predict_student_drop_risk(db, s.id)
        
        recs = db.query(Attendance).filter(Attendance.student_id == s.id).all()
        tot = len(recs)
        att = sum(1 for r in recs if r.status == AttendanceStatus.present)
        pct = (att / tot * 100.0) if tot > 0 else 100.0

        risk_lvl = "low"
        if prob >= 0.70:
            risk_lvl = "critical"
        elif prob >= 0.45:
            risk_lvl = "high"
        elif prob >= 0.25:
            risk_lvl = "medium"

        res.append(RiskPredictionOut(
            student_id=s.id,
            student_name=s.name,
            usn=s.usn,
            current_percentage=round(pct, 1),
            predicted_probability_drop=prob,
            risk_level=risk_lvl
        ))
    
    return sorted(res, key=lambda x: x.predicted_probability_drop, reverse=True)


@router.get("/student-profile/{student_id}")
def get_detailed_student_profile(student_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(404, "Student profile not found")

    classroom = db.query(ClassRoom).filter(ClassRoom.id == student.class_id).first()
    subjects = db.query(Subject).filter(Subject.class_id == student.class_id).all()
    records = db.query(Attendance).filter(Attendance.student_id == student.id).all()

    total_classes = len(records)
    total_attended = sum(1 for r in records if r.status == AttendanceStatus.present)
    overall_pct = (total_attended / total_classes * 100.0) if total_classes > 0 else 100.0

    alerts = db.query(Alert).filter(Alert.student_id == student_id).all()
    patterns = [a.type for a in alerts]

    highest_risk = "Low"
    if any(a.level.value == "critical" or a.level.value == "high" for a in alerts if hasattr(a.level, 'value')):
        highest_risk = "High"
    elif any(a.level.value == "medium" for a in alerts if hasattr(a.level, 'value')):
        highest_risk = "Medium"

    # Subject breakdown
    subject_details = []
    for s in subjects:
        sub_recs = [r for r in records if r.subject_id == s.id]
        sub_tot = len(sub_recs)
        sub_att = sum(1 for r in sub_recs if r.status == AttendanceStatus.present)
        sub_pct = (sub_att / sub_tot * 100.0) if sub_tot > 0 else 100.0

        calc = calculate_classes_needed(sub_att, sub_tot, settings.ATTENDANCE_THRESHOLD)

        # Monthly trend
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

        subject_details.append({
            "subject_id": s.id,
            "name": s.name,
            "code": s.code,
            "attended": sub_att,
            "total": sub_tot,
            "percentage": round(sub_pct, 1),
            "classes_needed": calc["classes_needed"],
            "safe_misses": calc["safe_misses"],
            "monthly_trend": monthly_trend
        })

    prob_drop = predict_student_drop_risk(db, student_id)
    points_8 = get_student_8_points_analysis(db, student_id)

    ai_reasons = []
    for a in alerts:
        if a.explanation and "reasons" in a.explanation:
            ai_reasons.extend(a.explanation["reasons"])

    return {
        "student": {
            "id": student.id,
            "name": student.name,
            "usn": student.usn,
            "email": student.email,
            "parent_email": student.parent_email,
            "class_name": classroom.name if classroom else "Class",
            "overall_pct": round(overall_pct, 1),
            "risk_level": highest_risk,
            "predicted_risk_prob": prob_drop,
            "detected_patterns": patterns if patterns else ["Normal Attendance"],
            "ai_summary": f"Overall attendance is {overall_pct:.1f}%. " + ("; ".join(ai_reasons) if ai_reasons else "Consistent attendance pattern maintained.")
        },
        "attendance_cutoff": settings.ATTENDANCE_THRESHOLD,
        "subjects": subject_details,
        "analysis_points": points_8,
        "alerts": [{"type": a.type, "score": a.risk_score, "level": a.level.value if hasattr(a.level, 'value') else a.level, "explanation": a.explanation} for a in alerts]
    }


@router.post("/student-profile/{student_id}/rerun-ai")
def rerun_student_ai_analysis(student_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(404, "Student not found")

    run_analytics_for_student(db, student_id)
    points_8 = get_student_8_points_analysis(db, student_id)

    return {
        "status": "success",
        "message": f"AI Analysis successfully updated for {student.name}",
        "analysis_points": points_8
    }


@router.get("/ai/health")
def get_ai_health():
    """Returns AI API Key health and connectivity diagnostic."""
    from app.services.openrouter_client import check_openrouter_health
    return check_openrouter_health()


@router.get("/student-profile/{student_id}/subject/{subject_id}")
def get_student_subject_trend(student_id: int, subject_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.services.analytics import get_student_subject_monthly_trend
    res = get_student_subject_monthly_trend(db, student_id, subject_id)
    if "error" in res:
        raise HTTPException(404, res["error"])
    return res


