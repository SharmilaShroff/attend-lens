from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.models import User, CounsellingCase, CounsellingMessage, Alert, Student, CaseStatus
from app.schemas.all_schemas import CounsellingCaseOut, CounsellingMessageCreate, CounsellingMessageOut
from app.services.counselling import create_or_get_counselling_case, send_counselling_case

router = APIRouter(prefix="/counselling", tags=["counselling"])


@router.post("/cases/from-alert/{alert_id}", response_model=CounsellingCaseOut)
def create_case(alert_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(404, "Alert not found")
    case = create_or_get_counselling_case(db, alert)
    out = CounsellingCaseOut.model_validate(case)
    st = db.query(Student).filter(Student.id == case.student_id).first()
    out.student_name = st.name if st else None
    return out


@router.post("/cases/{case_id}/send", response_model=CounsellingCaseOut)
def dispatch_case(case_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    case = send_counselling_case(db, case_id)
    out = CounsellingCaseOut.model_validate(case)
    st = db.query(Student).filter(Student.id == case.student_id).first()
    out.student_name = st.name if st else None
    return out


@router.post("/cases/{case_id}/reply", response_model=CounsellingMessageOut)
def reply_case(case_id: int, body: CounsellingMessageCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    case = db.query(CounsellingCase).filter(CounsellingCase.id == case_id).first()
    if not case:
        raise HTTPException(404, "Case not found")

    sender_type = "student" if user.role == "student" else "staff"
    msg = CounsellingMessage(
        case_id=case_id,
        sender=sender_type,
        channel="app",
        body=body.body
    )
    db.add(msg)

    # Update case status if student responded
    if sender_type == "student":
        case.status = CaseStatus.responded
        case.responded_at = msg.created_at

    db.commit()
    db.refresh(msg)
    return CounsellingMessageOut.model_validate(msg)
