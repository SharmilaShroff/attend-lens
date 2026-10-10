from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.models import User, Intervention, Student, Attendance, AttendanceStatus
from app.schemas.all_schemas import InterventionCreate, InterventionOut

router = APIRouter(prefix="/interventions", tags=["interventions"])


@router.post("", response_model=InterventionOut)
def record_intervention(body: InterventionCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Calculate current attendance snapshot before intervention
    records = db.query(Attendance).filter(Attendance.student_id == body.student_id).all()
    total = len(records)
    attended = sum(1 for r in records if r.status == AttendanceStatus.present)
    snapshot = (attended / total * 100.0) if total > 0 else None

    i = Intervention(
        student_id=body.student_id,
        alert_id=body.alert_id,
        staff_id=user.id,
        type=body.type,
        notes=body.notes,
        date=date.today(),
        outcome=body.outcome,
        attendance_before=snapshot
    )
    db.add(i)
    db.commit()
    db.refresh(i)

    out = InterventionOut.model_validate(i)
    st = db.query(Student).filter(Student.id == i.student_id).first()
    u = db.query(User).filter(User.id == i.staff_id).first() if i.staff_id else None
    out.student_name = st.name if st else None
    out.staff_name = u.name if u else "System"
    return out


@router.get("/student/{student_id}", response_model=list[InterventionOut])
def get_student_interventions(student_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    interventions = db.query(Intervention).filter(Intervention.student_id == student_id).order_by(Intervention.created_at.desc()).all()
    
    # Calculate latest attendance snapshot for comparison
    records = db.query(Attendance).filter(Attendance.student_id == student_id).all()
    total = len(records)
    attended = sum(1 for r in records if r.status == AttendanceStatus.present)
    current_snapshot = (attended / total * 100.0) if total > 0 else None

    res = []
    for i in interventions:
        out = InterventionOut.model_validate(i)
        st = db.query(Student).filter(Student.id == i.student_id).first()
        u = db.query(User).filter(User.id == i.staff_id).first() if i.staff_id else None
        out.student_name = st.name if st else None
        out.staff_name = u.name if u else "System"
        out.attendance_after = current_snapshot
        res.append(out)
    return res
