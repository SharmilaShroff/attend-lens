import io
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.models import (
    User, Mentor, Teacher, ClassRoom, Student, Subject, TeacherClassSubject, Role
)
from app.schemas.all_schemas import (
    ClassCreate, ClassUpdate, ClassOut, StudentCreate, StudentUpdate, StudentOut,
    StudentImportSummary, SubjectOut
)
from app.security import hash_password

router = APIRouter(prefix="/mentor", tags=["mentor"])


def require_mentor(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Mentor:
    if user.role != Role.mentor:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Mentor access required")
    mentor = db.query(Mentor).filter(Mentor.user_id == user.id).first()
    if not mentor:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mentor profile not found")
    return mentor


# --- Class Management ---
@router.post("/classes", response_model=ClassOut)
def create_class(body: ClassCreate, mentor: Mentor = Depends(require_mentor), db: Session = Depends(get_db)):
    c = ClassRoom(
        mentor_id=mentor.id,
        name=body.name,
        branch=body.branch,
        semester=body.semester,
        section=body.section,
        academic_year=body.academic_year
    )
    db.add(c)
    db.commit()
    db.refresh(c)

    # Auto-create core distinct subjects for class attendance graphs
    sem = body.semester or 6
    default_subjects = [
        ("Database Management Systems", f"CS{sem}01"),
        ("Machine Learning", f"CS{sem}02"),
        ("Computer Networks", f"CS{sem}03"),
        ("Web Technologies", f"CS{sem}04"),
        ("Software Engineering", f"CS{sem}05")
    ]
    for sub_name, sub_code in default_subjects:
        sub = Subject(class_id=c.id, name=sub_name, code=sub_code)
        db.add(sub)
    db.commit()

    return ClassOut.model_validate(c)



@router.get("/classes", response_model=list[ClassOut])
def list_classes(mentor: Mentor = Depends(require_mentor), db: Session = Depends(get_db)):
    classes = db.query(ClassRoom).filter(ClassRoom.mentor_id == mentor.id).all()
    res = []
    for c in classes:
        out = ClassOut.model_validate(c)
        out.student_count = db.query(Student).filter(Student.class_id == c.id).count()
        out.subject_count = db.query(Subject).filter(Subject.class_id == c.id).count()
        res.append(out)
    return res


@router.put("/classes/{class_id}", response_model=ClassOut)
def update_class(class_id: int, body: ClassUpdate, mentor: Mentor = Depends(require_mentor), db: Session = Depends(get_db)):
    c = db.query(ClassRoom).filter(ClassRoom.id == class_id, ClassRoom.mentor_id == mentor.id).first()
    if not c:
        raise HTTPException(404, "Class not found")
    for key, val in body.model_dump(exclude_unset=True).items():
        setattr(c, key, val)
    db.commit()
    db.refresh(c)
    return ClassOut.model_validate(c)


@router.delete("/classes/{class_id}", status_code=204)
def delete_class(class_id: int, mentor: Mentor = Depends(require_mentor), db: Session = Depends(get_db)):
    c = db.query(ClassRoom).filter(ClassRoom.id == class_id, ClassRoom.mentor_id == mentor.id).first()
    if not c:
        raise HTTPException(404, "Class not found")
    db.delete(c)
    db.commit()


# --- Student Management & Import ---
@router.post("/students", response_model=StudentOut)
def add_student_manual(body: StudentCreate, mentor: Mentor = Depends(require_mentor), db: Session = Depends(get_db)):
    existing = db.query(Student).filter(Student.usn == body.usn.strip().upper()).first()
    if existing:
        raise HTTPException(400, f"Student with USN {body.usn} already exists")

    user = User(
        role=Role.student,
        name=body.name,
        email=body.email,
        usn=body.usn.strip().upper(),
        password_hash=hash_password(body.usn.strip().upper()),
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    s = Student(
        user_id=user.id,
        class_id=body.class_id,
        name=body.name,
        usn=body.usn.strip().upper(),
        email=body.email,
        parent_email=body.parent_email,
        parent_phone=body.parent_phone
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return StudentOut.model_validate(s)


@router.get("/classes/{class_id}/students", response_model=list[StudentOut])
def get_class_students(class_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    students = db.query(Student).filter(Student.class_id == class_id).all()
    return [StudentOut.model_validate(s) for s in students]


@router.post("/classes/{class_id}/import-students", response_model=StudentImportSummary)
def import_students_file(
    class_id: int,
    file: UploadFile = File(...),
    mentor: Mentor = Depends(require_mentor),
    db: Session = Depends(get_db)
):
    contents = file.file.read()
    filename = file.filename.lower()

    try:
        if filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(contents))
        elif filename.endswith((".xls", ".xlsx")):
            df = pd.read_excel(io.BytesIO(contents))
        else:
            raise HTTPException(400, "Only CSV or Excel (.xlsx) files are supported")
    except Exception as e:
        raise HTTPException(400, f"Failed to parse file: {str(e)}")

    required_cols = {'name', 'usn'}
    df_cols = {str(c).strip().lower() for c in df.columns}
    if not required_cols.issubset(df_cols):
        raise HTTPException(400, f"File must contain at least 'name' and 'usn' columns. Found: {list(df.columns)}")

    df.columns = [str(c).strip().lower() for c in df.columns]

    added = 0
    skipped = 0
    errors = []

    for idx, row in df.iterrows():
        try:
            name = str(row['name']).strip()
            usn = str(row['usn']).strip().upper()
            email = str(row['email']).strip() if 'email' in row and pd.notna(row['email']) else None
            p_email = str(row['parent_email']).strip() if 'parent_email' in row and pd.notna(row['parent_email']) else None
            p_phone = str(row['parent_phone']).strip() if 'parent_phone' in row and pd.notna(row['parent_phone']) else None

            if not name or not usn:
                skipped += 1
                errors.append(f"Row {idx+2}: Missing name or USN")
                continue

            existing = db.query(Student).filter(Student.usn == usn).first()
            if existing:
                skipped += 1
                errors.append(f"Row {idx+2}: Duplicate USN '{usn}' skipped")
                continue

            user = User(
                role=Role.student,
                name=name,
                email=email,
                usn=usn,
                password_hash=hash_password(usn),
                is_active=True
            )
            db.add(user)
            db.commit()

            s = Student(
                user_id=user.id,
                class_id=class_id,
                name=name,
                usn=usn,
                email=email,
                parent_email=p_email,
                parent_phone=p_phone
            )
            db.add(s)
            db.commit()
            added += 1
        except Exception as ex:
            db.rollback()
            skipped += 1
            errors.append(f"Row {idx+2}: {str(ex)}")

    return StudentImportSummary(added_count=added, skipped_count=skipped, errors=errors)


@router.get("/classes/{class_id}/subjects", response_model=list[SubjectOut])
def get_class_subjects(class_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    subjects = db.query(Subject).filter(Subject.class_id == class_id).all()
    res = []
    for s in subjects:
        out = SubjectOut.model_validate(s)
        tcs = db.query(TeacherClassSubject).filter(TeacherClassSubject.subject_id == s.id).first()
        if tcs:
            t = db.query(Teacher).filter(Teacher.id == tcs.teacher_id).first()
            if t and t.user:
                out.teacher_name = t.user.name
                out.teacher_id = t.id
        res.append(out)
    return res
