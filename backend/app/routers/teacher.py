from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.models import (
    User, Teacher, ClassRoom, Subject, TeacherClassSubject, Attendance,
    AttendanceAuditLog, Role, AttendanceStatus, Student
)
from app.schemas.all_schemas import (
    AttendanceMarkRequest, AttendanceOut, AttendanceAuditLogOut, ClassOut
)
from app.services.analytics import run_analytics_for_student

router = APIRouter(prefix="/teacher", tags=["teacher"])


def require_teacher(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Teacher:
    if user.role not in [Role.teacher, Role.mentor]:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Teacher or Mentor access required")
    teacher = db.query(Teacher).filter(Teacher.user_id == user.id).first()
    if not teacher and user.role == Role.mentor:
        # Auto-create teacher profile for mentor if needed
        teacher = Teacher(user_id=user.id, department="General")
        db.add(teacher)
        db.commit()
        db.refresh(teacher)
    if not teacher:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Teacher profile not found")
    return teacher


@router.get("/available-classes", response_model=list[ClassOut])
def get_all_classes(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """All classes created in system that a teacher can select."""
    classes = db.query(ClassRoom).all()
    res = []
    for c in classes:
        out = ClassOut.model_validate(c)
        out.student_count = db.query(Student).filter(Student.class_id == c.id).count()
        out.subject_count = db.query(Subject).filter(Subject.class_id == c.id).count()
        res.append(out)
    return res


@router.get("/my-classes", response_model=list[ClassOut])
def get_teacher_selected_classes(teacher: Teacher = Depends(require_teacher), db: Session = Depends(get_db)):
    mappings = db.query(TeacherClassSubject).filter(TeacherClassSubject.teacher_id == teacher.id).all()
    class_ids = list(set([m.class_id for m in mappings]))
    classes = db.query(ClassRoom).filter(ClassRoom.id.in_(class_ids)).all() if class_ids else []

    res = []
    for c in classes:
        out = ClassOut.model_validate(c)
        out.student_count = db.query(Student).filter(Student.class_id == c.id).count()
        out.subject_count = db.query(Subject).filter(Subject.class_id == c.id).count()
        res.append(out)
    return res


@router.post("/select-class/{class_id}", status_code=200)
def select_class(class_id: int, teacher: Teacher = Depends(require_teacher), db: Session = Depends(get_db)):
    subjects = db.query(Subject).filter(Subject.class_id == class_id).all()
    if not subjects:
        # Create a default subject mapping if none exist
        sub = Subject(class_id=class_id, name="General Subject", code=f"GEN-{class_id}")
        db.add(sub)
        db.commit()
        db.refresh(sub)
        subjects = [sub]

    for sub in subjects:
        existing = db.query(TeacherClassSubject).filter(
            TeacherClassSubject.teacher_id == teacher.id,
            TeacherClassSubject.class_id == class_id,
            TeacherClassSubject.subject_id == sub.id
        ).first()
        if not existing:
            tcs = TeacherClassSubject(
                teacher_id=teacher.id,
                class_id=class_id,
                subject_id=sub.id,
                assigned_by_mentor=False
            )
            db.add(tcs)
    db.commit()
    return {"message": "Class selected successfully"}


@router.delete("/remove-class/{class_id}", status_code=200)
def remove_class(class_id: int, teacher: Teacher = Depends(require_teacher), db: Session = Depends(get_db)):
    db.query(TeacherClassSubject).filter(
        TeacherClassSubject.teacher_id == teacher.id,
        TeacherClassSubject.class_id == class_id
    ).delete()
    db.commit()
    return {"message": "Class removed from teacher list"}


# --- Attendance Marking & Audit Log Overwriting ---
@router.post("/mark-attendance", status_code=200)
def mark_attendance(body: AttendanceMarkRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    updated_students = set()

    for item in body.items:
        existing = db.query(Attendance).filter(
            Attendance.student_id == item.student_id,
            Attendance.subject_id == body.subject_id,
            Attendance.date == body.date,
            Attendance.period == body.period
        ).first()

        new_status_str = item.status.value if hasattr(item.status, 'value') else str(item.status)

        if existing:
            old_status_str = existing.status.value if hasattr(existing.status, 'value') else str(existing.status)
            if old_status_str != new_status_str:
                # Audit Log Entry
                audit = AttendanceAuditLog(
                    attendance_id=existing.id,
                    student_id=item.student_id,
                    subject_id=body.subject_id,
                    date=body.date,
                    period=body.period,
                    old_status=old_status_str,
                    new_status=new_status_str,
                    changed_by=user.id,
                    reason="Updated via attendance grid"
                )
                db.add(audit)
                existing.status = item.status
                existing.marked_by = user.id
        else:
            # New attendance record
            att = Attendance(
                student_id=item.student_id,
                subject_id=body.subject_id,
                date=body.date,
                period=body.period,
                status=item.status,
                marked_by=user.id
            )
            db.add(att)
            db.flush()

            audit = AttendanceAuditLog(
                attendance_id=att.id,
                student_id=item.student_id,
                subject_id=body.subject_id,
                date=body.date,
                period=body.period,
                old_status=None,
                new_status=new_status_str,
                changed_by=user.id,
                reason="Initial attendance marking"
            )
            db.add(audit)

        updated_students.add(item.student_id)

    db.commit()

    # Trigger background AI analytics for updated students
    for s_id in updated_students:
        try:
            run_analytics_for_student(db, s_id)
        except Exception as e:
            print(f"[ANALYTICS TRIGGER ERROR] {e}")

    return {"message": f"Attendance marked/updated for {len(body.items)} students"}


@router.get("/attendance-records")
def get_attendance_records(
    class_id: int, subject_id: int, date: date, period: int = 1,
    db: Session = Depends(get_db)
):
    students = db.query(Student).filter(Student.class_id == class_id).all()
    records = db.query(Attendance).filter(
        Attendance.subject_id == subject_id,
        Attendance.date == date,
        Attendance.period == period
    ).all()

    record_map = {r.student_id: r.status.value for r in records}

    res = []
    for s in students:
        res.append({
            "student_id": s.id,
            "student_name": s.name,
            "usn": s.usn,
            "status": record_map.get(s.id, "not_marked")  # Explicit "Not marked"
        })
    return res


@router.get("/audit-logs", response_model=list[AttendanceAuditLogOut])
def get_audit_logs(class_id: int, db: Session = Depends(get_db)):
    students = db.query(Student).filter(Student.class_id == class_id).all()
    student_ids = [s.id for s in students]
    logs = db.query(AttendanceAuditLog).filter(AttendanceAuditLog.student_id.in_(student_ids)).order_by(AttendanceAuditLog.changed_at.desc()).limit(50).all()

    res = []
    for log in logs:
        out = AttendanceAuditLogOut.model_validate(log)
        st = db.query(Student).filter(Student.id == log.student_id).first()
        sb = db.query(Subject).filter(Subject.id == log.subject_id).first()
        u = db.query(User).filter(User.id == log.changed_by).first() if log.changed_by else None

        out.student_name = st.name if st else None
        out.subject_name = sb.name if sb else None
        out.changed_by_name = u.name if u else "System"
        res.append(out)
    return res
