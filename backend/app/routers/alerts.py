from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.models import User, Alert, AlertStatus, Student, Subject, Role, RiskLevel
from app.schemas.all_schemas import AlertOut, AlertOverrideRequest, AlertDismissRequest

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertOut])
def list_alerts(
    class_id: int | None = None,
    status_filter: str | None = "open",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Alert)

    if class_id:
        students = db.query(Student).filter(Student.class_id == class_id).all()
        student_ids = [s.id for s in students]
        query = query.filter(Alert.student_id.in_(student_ids))

    if status_filter and status_filter != "all":
        query = query.filter(Alert.status == AlertStatus(status_filter))

    alerts = query.order_by(Alert.risk_score.desc()).all()
    res = []
    for a in alerts:
        out = AlertOut.model_validate(a)
        st = db.query(Student).filter(Student.id == a.student_id).first()
        sb = db.query(Subject).filter(Subject.id == a.subject_id).first() if a.subject_id else None
        u = db.query(User).filter(User.id == a.dismissed_by).first() if a.dismissed_by else None

        out.student_name = st.name if st else None
        out.subject_name = sb.name if sb else "Overall"
        out.dismissed_by_name = u.name if u else None
        res.append(out)
    return res


@router.get("/{alert_id}", response_model=AlertOut)
def get_alert_explain(alert_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    a = db.query(Alert).filter(Alert.id == alert_id).first()
    if not a:
        raise HTTPException(404, "Alert not found")

    out = AlertOut.model_validate(a)
    st = db.query(Student).filter(Student.id == a.student_id).first()
    sb = db.query(Subject).filter(Subject.id == a.subject_id).first() if a.subject_id else None
    out.student_name = st.name if st else None
    out.subject_name = sb.name if sb else "Overall"
    return out


@router.post("/{alert_id}/override", response_model=AlertOut)
def override_alert_severity(
    alert_id: int,
    body: AlertOverrideRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if user.role not in [Role.mentor, Role.teacher]:
        raise HTTPException(403, "Staff access required")
    a = db.query(Alert).filter(Alert.id == alert_id).first()
    if not a:
        raise HTTPException(404, "Alert not found")

    a.override_level = body.override_level
    a.override_reason = body.reason
    db.commit()
    db.refresh(a)
    return AlertOut.model_validate(a)


@router.post("/{alert_id}/dismiss", response_model=AlertOut)
def dismiss_alert(
    alert_id: int,
    body: AlertDismissRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if user.role not in [Role.mentor, Role.teacher]:
        raise HTTPException(403, "Staff access required")
    a = db.query(Alert).filter(Alert.id == alert_id).first()
    if not a:
        raise HTTPException(404, "Alert not found")

    a.status = AlertStatus.dismissed
    a.dismissed_by = user.id
    a.dismissed_reason = body.reason
    a.dismissed_score = a.risk_score
    db.commit()
    db.refresh(a)
    return AlertOut.model_validate(a)
