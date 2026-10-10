"""/auth: login (email or USN), current user, change password."""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Mentor, Role, Student, Teacher, User
from app.schemas.auth import ChangePasswordRequest, LoginRequest, TokenResponse, UserOut
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])

BAD_CREDENTIALS = HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect credentials")


def _authenticate(db: Session, role: str, identifier: str, password: str) -> User:
    ident = identifier.strip()
    q = db.query(User).filter(User.role == Role(role))
    # Students sign in with USN (case-insensitive), staff with email.
    user = q.filter(User.usn == ident.upper()).first() if role == "student" \
        else q.filter(User.email == ident.lower()).first()
    if not user or not user.is_active or not verify_password(password, user.password_hash):
        raise BAD_CREDENTIALS  # same error for unknown user / wrong password: no account enumeration
    return user


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = _authenticate(db, body.role, body.identifier, body.password)
    return TokenResponse(access_token=create_access_token(user.id, user.role.value),
                         role=user.role.value, name=user.name)


@router.post("/login/form", response_model=TokenResponse, include_in_schema=True)
def login_form(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Swagger 'Authorize' button support. username = email (staff) or USN (student)."""
    ident = form.username.strip()
    user = db.query(User).filter((User.email == ident.lower()) | (User.usn == ident.upper())).first()
    if not user or not verify_password(form.password, user.password_hash):
        raise BAD_CREDENTIALS
    return TokenResponse(access_token=create_access_token(user.id, user.role.value),
                         role=user.role.value, name=user.name)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile_id = class_id = None
    if user.role == Role.mentor:
        m = db.query(Mentor).filter(Mentor.user_id == user.id).first()
        profile_id = m.id if m else None
    elif user.role == Role.teacher:
        t = db.query(Teacher).filter(Teacher.user_id == user.id).first()
        profile_id = t.id if t else None
    else:
        s = db.query(Student).filter(Student.user_id == user.id).first()
        profile_id, class_id = (s.id, s.class_id) if s else (None, None)
    return UserOut(id=user.id, role=user.role.value, name=user.name, email=user.email,
                   usn=user.usn, profile_id=profile_id, class_id=class_id)


@router.post("/change-password", status_code=204)
def change_password(body: ChangePasswordRequest, user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Current password is incorrect")
    user.password_hash = hash_password(body.new_password)
    db.commit()
