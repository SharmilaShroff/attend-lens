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

        # Generate human counsellor AI response using OpenRouter
        student = db.query(Student).filter(Student.id == case.student_id).first()
        if student:
            try:
                from app.services.counselling import generate_counselling_reply, generate_and_save_counselling_summary

                ai_body, pred = generate_counselling_reply(student, case, body.body, db=db)

                ai_msg = CounsellingMessage(
                    case_id=case_id,
                    sender="ai",
                    channel="app",
                    body=ai_body
                )
                db.add(ai_msg)
                db.commit()

                # Generate/update Counselling Summary in mentor's Remarks
                generate_and_save_counselling_summary(db, case_id)
            except Exception as e:
                print(f"[Error generating AI counselling reply] {e}")

    db.commit()
    db.refresh(msg)
    return CounsellingMessageOut.model_validate(msg)


@router.get("/cases", response_model=list[CounsellingCaseOut])
def list_counselling_cases(student_id: int | None = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(CounsellingCase)
    if student_id:
        query = query.filter(CounsellingCase.student_id == student_id)
    cases = query.order_by(CounsellingCase.created_at.desc()).all()
    res = []

    for c in cases:
        out = CounsellingCaseOut.model_validate(c)
        st = db.query(Student).filter(Student.id == c.student_id).first()
        out.student_name = st.name if st else None
        res.append(out)
    return res

