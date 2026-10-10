import os
import sys
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.database import get_db
from app.deps import get_current_user
from app.models.models import User, Student, Attendance, Subject, AttendanceStatus
from app.config import get_settings

settings = get_settings()

router = APIRouter(prefix="/api/ml", tags=["ml"])

# Dynamically add ML module to sys.path
try:
    ml_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../ml"))
    if ml_path not in sys.path:
        sys.path.append(ml_path)
    from src.predict import predict_counsel
except Exception as e:
    predict_counsel = None
    print(f"Failed to import predict_counsel: {e}")

class MLCounselRequest(BaseModel):
    student_id: int
    reason_text: str | None = None

def compute_attendance_features(db: Session, student_id: int) -> dict:
    records = db.query(Attendance).filter(Attendance.student_id == student_id).order_by(Attendance.date.desc()).all()
    if not records:
        return {
            "overall_pct": 100.0,
            "subjects_below_75": 0,
            "consecutive_streak": 0,
            "monday_ratio": 0.0,
            "friday_ratio": 0.0,
            "recent_trend": 0.0
        }
        
    total_classes = len(records)
    total_present = sum(1 for r in records if (r.status.value if hasattr(r.status, "value") else str(r.status)) == "present")
    overall_pct = (total_present / total_classes) * 100.0
    
    subjects = set(r.subject_id for r in records)
    subjects_below_75 = 0
    for subj in subjects:
        sub_recs = [r for r in records if r.subject_id == subj]
        sub_present = sum(1 for r in sub_recs if (r.status.value if hasattr(r.status, "value") else str(r.status)) == "present")
        if (sub_present / len(sub_recs)) * 100.0 < 75.0:
            subjects_below_75 += 1
            
    streak = 0
    for r in records:
        status_val = r.status.value if hasattr(r.status, "value") else str(r.status)
        if status_val != "present":
            streak += 1
        else:
            break
            
    monday_total = 0
    monday_absent = 0
    friday_total = 0
    friday_absent = 0
    
    for r in records:
        dt = datetime.strptime(r.date, "%Y-%m-%d") if isinstance(r.date, str) else r.date
        if dt.weekday() == 0:
            monday_total += 1
            if (r.status.value if hasattr(r.status, "value") else str(r.status)) != "present":
                monday_absent += 1
        elif dt.weekday() == 4:
            friday_total += 1
            if (r.status.value if hasattr(r.status, "value") else str(r.status)) != "present":
                friday_absent += 1
                
    monday_ratio = monday_absent / monday_total if monday_total else 0.0
    friday_ratio = friday_absent / friday_total if friday_total else 0.0
    
    max_date = datetime.strptime(records[0].date, "%Y-%m-%d") if isinstance(records[0].date, str) else records[0].date
    l14_start = max_date - timedelta(days=14)
    p14_start = l14_start - timedelta(days=14)
    
    l14_recs = [r for r in records if (datetime.strptime(r.date, "%Y-%m-%d") if isinstance(r.date, str) else r.date) > l14_start]
    p14_recs = [r for r in records if p14_start < (datetime.strptime(r.date, "%Y-%m-%d") if isinstance(r.date, str) else r.date) <= l14_start]
            
    def get_pct(recs):
        if not recs: return 100.0
        p = sum(1 for r in recs if (r.status.value if hasattr(r.status, "value") else str(r.status)) == "present")
        return (p / len(recs)) * 100.0
        
    l14_pct = get_pct(l14_recs)
    p14_pct = get_pct(p14_recs)
    recent_trend = l14_pct - p14_pct
    
    return {
        "overall_pct": overall_pct,
        "subjects_below_75": subjects_below_75,
        "consecutive_streak": streak,
        "monday_ratio": monday_ratio,
        "friday_ratio": friday_ratio,
        "recent_trend": recent_trend
    }

@router.post("/counsel")
def ml_predict_counsel(
    req: MLCounselRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    if not predict_counsel:
        raise HTTPException(status_code=503, detail="ML module not available")
        
    try:
        features = compute_attendance_features(db, req.student_id)
        prediction = predict_counsel(features, req.reason_text)
        return prediction
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
