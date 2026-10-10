from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.models import User, Remark, Student, Role
from app.schemas.all_schemas import RemarkCreate, RemarkOut

router = APIRouter(prefix="/remarks", tags=["remarks"])


@router.post("", response_model=RemarkOut)
def add_remark(body: RemarkCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    r = Remark(
        student_id=body.student_id,
        author_id=user.id,
        role=user.role,
        text=body.text
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    out = RemarkOut.model_validate(r)
    out.author_name = user.name
    return out


@router.get("/my-remarks", response_model=list[RemarkOut])
def get_my_remarks(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can access this endpoint")
    
    st = db.query(Student).filter(Student.user_id == user.id).first()
    if not st and user.usn:
        st = db.query(Student).filter(Student.usn == user.usn).first()
    if not st:
        return []
        
    remarks = db.query(Remark).filter(
        Remark.student_id == st.id,
        Remark.role == Role.mentor,
        ~Remark.text.contains("Counselling Summary")
    ).order_by(Remark.created_at.desc()).all()
    
    res = []
    for r in remarks:
        out = RemarkOut.model_validate(r)
        u = db.query(User).filter(User.id == r.author_id).first()
        out.author_name = u.name if u else "Mentor"
        res.append(out)
    return res


@router.get("/student/{student_id}", response_model=list[RemarkOut])
def get_student_remarks(student_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role == "student":
        st = db.query(Student).filter(Student.user_id == user.id).first()
        if not st and user.usn:
            st = db.query(Student).filter(Student.usn == user.usn).first()
        if not st or st.id != student_id:
            raise HTTPException(status_code=403, detail="Access denied: You can only view your own remarks.")

    query = db.query(Remark).filter(Remark.student_id == student_id)
    
    # Counselling summaries are visible only to mentors/teachers, not on student dashboard
    # Students see only mentor written remarks
    if user.role == "student":
        query = query.filter(
            Remark.role == Role.mentor,
            ~Remark.text.contains("Counselling Summary")
        )
        
    remarks = query.order_by(Remark.created_at.desc()).all()
    res = []
    for r in remarks:
        out = RemarkOut.model_validate(r)
        u = db.query(User).filter(User.id == r.author_id).first()
        out.author_name = u.name if u else "Staff"
        res.append(out)
    return res
