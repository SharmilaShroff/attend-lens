"""Reusable FastAPI dependencies: current user + role guards."""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Mentor, Role, Student, Teacher, User
from app.security import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login/form")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token",
                            headers={"WWW-Authenticate": "Bearer"})
    user = db.get(User, int(payload["sub"]))
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found or inactive")
    return user


def require_roles(*roles: Role):
    """Dependency factory: `Depends(require_roles(Role.mentor))` -> 403 for any other role."""
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "You do not have access to this resource")
        return user
    return checker


require_mentor = require_roles(Role.mentor)
require_teacher = require_roles(Role.teacher)
require_student = require_roles(Role.student)
require_staff = require_roles(Role.mentor, Role.teacher)


def get_current_mentor(user: User = Depends(require_mentor), db: Session = Depends(get_db)) -> Mentor:
    mentor = db.query(Mentor).filter(Mentor.user_id == user.id).first()
    if not mentor:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mentor profile missing")
    return mentor


def get_current_teacher(user: User = Depends(require_teacher), db: Session = Depends(get_db)) -> Teacher:
    teacher = db.query(Teacher).filter(Teacher.user_id == user.id).first()
    if not teacher:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Teacher profile missing")
    return teacher


def get_current_student(user: User = Depends(require_student), db: Session = Depends(get_db)) -> Student:
    student = db.query(Student).filter(Student.user_id == user.id).first()
    if not student:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Student profile missing")
    return student
