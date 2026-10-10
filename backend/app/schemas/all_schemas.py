from datetime import date, datetime
from typing import Any, Optional
from pydantic import BaseModel, EmailStr, Field
from app.models.models import Role, RiskLevel, AlertStatus, CaseStatus, ReasonStatus, AttendanceStatus


# --- Auth Schemas ---
class LoginRequest(BaseModel):
    role: str
    identifier: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    name: str


class UserOut(BaseModel):
    id: int
    role: str
    name: str
    email: Optional[str] = None
    usn: Optional[str] = None
    profile_id: Optional[int] = None
    class_id: Optional[int] = None

    class Config:
        from_attributes = True


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


# --- Class Schemas ---
class ClassCreate(BaseModel):
    name: str
    branch: str
    semester: int
    section: Optional[str] = None
    academic_year: str


class ClassUpdate(BaseModel):
    name: Optional[str] = None
    branch: Optional[str] = None
    semester: Optional[int] = None
    section: Optional[str] = None
    academic_year: Optional[str] = None


class ClassOut(BaseModel):
    id: int
    mentor_id: int
    name: str
    branch: str
    semester: int
    section: Optional[str] = None
    academic_year: str
    created_at: datetime
    student_count: Optional[int] = 0
    subject_count: Optional[int] = 0

    class Config:
        from_attributes = True


# --- Student Schemas ---
class StudentCreate(BaseModel):
    class_id: int
    name: str
    usn: str
    email: Optional[str] = None
    parent_email: Optional[str] = None
    parent_phone: Optional[str] = None


class StudentUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    parent_email: Optional[str] = None
    parent_phone: Optional[str] = None


class StudentOut(BaseModel):
    id: int
    user_id: Optional[int] = None
    class_id: int
    name: str
    usn: str
    email: Optional[str] = None
    parent_email: Optional[str] = None
    parent_phone: Optional[str] = None
    overall_attendance_pct: Optional[float] = 0.0
    risk_level: Optional[str] = "low"
    created_at: datetime

    class Config:
        from_attributes = True


class StudentImportSummary(BaseModel):
    added_count: int
    skipped_count: int
    errors: list[str]


# --- Subject Schemas ---
class SubjectCreate(BaseModel):
    class_id: int
    name: str
    code: str


class SubjectOut(BaseModel):
    id: int
    class_id: int
    name: str
    code: str
    teacher_name: Optional[str] = None
    teacher_id: Optional[int] = None

    class Config:
        from_attributes = True


class TeacherAssignRequest(BaseModel):
    teacher_id: int
    class_id: int
    subject_id: int


# --- Attendance Schemas ---
class AttendanceMarkItem(BaseModel):
    student_id: int
    status: AttendanceStatus


class AttendanceMarkRequest(BaseModel):
    class_id: int
    subject_id: int
    date: date
    period: int = 1
    items: list[AttendanceMarkItem]


class AttendanceOut(BaseModel):
    id: int
    student_id: int
    subject_id: int
    date: date
    period: int
    status: AttendanceStatus
    marked_by: Optional[int] = None
    updated_at: datetime

    class Config:
        from_attributes = True


class AttendanceAuditLogOut(BaseModel):
    id: int
    attendance_id: Optional[int] = None
    student_id: int
    student_name: Optional[str] = None
    subject_id: int
    subject_name: Optional[str] = None
    date: date
    period: int
    old_status: Optional[str] = None
    new_status: str
    changed_by_name: Optional[str] = None
    changed_at: datetime
    reason: Optional[str] = None

    class Config:
        from_attributes = True


class SubjectAttendanceSummary(BaseModel):
    subject_id: int
    subject_name: str
    subject_code: str
    attended: int
    total: int
    percentage: float
    classes_needed: int
    safe_misses: int
    monthly_trend: list[dict[str, Any]] = []


# --- Remarks & Absence Reasons ---
class RemarkCreate(BaseModel):
    student_id: int
    text: str


class RemarkOut(BaseModel):
    id: int
    student_id: int
    author_id: int
    author_name: Optional[str] = None
    role: str
    text: str
    created_at: datetime

    class Config:
        from_attributes = True


class AbsenceReasonCreate(BaseModel):
    subject_id: Optional[int] = None
    date: date
    category: str
    reason: str
    proof_path: Optional[str] = None


class AbsenceReasonReview(BaseModel):
    status: ReasonStatus
    review_note: Optional[str] = None


class AbsenceReasonOut(BaseModel):
    id: int
    student_id: int
    student_name: Optional[str] = None
    subject_id: Optional[int] = None
    subject_name: Optional[str] = None
    date: date
    category: str
    reason: str
    proof_path: Optional[str] = None
    status: ReasonStatus
    reviewed_by_name: Optional[str] = None
    review_note: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# --- Alert Schemas ---
class AlertOut(BaseModel):
    id: int
    student_id: int
    student_name: Optional[str] = None
    subject_id: Optional[int] = None
    subject_name: Optional[str] = None
    type: str
    risk_score: float
    level: RiskLevel
    explanation: dict[str, Any]
    status: AlertStatus
    override_level: Optional[RiskLevel] = None
    override_reason: Optional[str] = None
    dismissed_by_name: Optional[str] = None
    dismissed_reason: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AlertOverrideRequest(BaseModel):
    override_level: RiskLevel
    reason: str


class AlertDismissRequest(BaseModel):
    reason: str


# --- Counselling & Interventions ---
class CounsellingMessageCreate(BaseModel):
    body: str


class CounsellingMessageOut(BaseModel):
    id: int
    case_id: int
    sender: str
    channel: str
    body: str
    created_at: datetime

    class Config:
        from_attributes = True


class CounsellingCaseOut(BaseModel):
    id: int
    alert_id: int
    student_id: int
    student_name: Optional[str] = None
    message: str
    status: CaseStatus
    sent_at: Optional[datetime] = None
    deadline_at: Optional[datetime] = None
    responded_at: Optional[datetime] = None
    escalated_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime
    messages: list[CounsellingMessageOut] = []
    ml_analysis: Optional[dict[str, Any]] = None

    class Config:
        from_attributes = True


class InterventionCreate(BaseModel):
    student_id: int
    alert_id: Optional[int] = None
    type: str
    notes: Optional[str] = None
    outcome: Optional[str] = None


class InterventionOut(BaseModel):
    id: int
    student_id: int
    student_name: Optional[str] = None
    staff_name: Optional[str] = None
    type: str
    notes: Optional[str] = None
    date: date
    outcome: Optional[str] = None
    attendance_before: Optional[float] = None
    attendance_after: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True


# --- Analytics & Chatbot ---
class RunAnalyticsResponse(BaseModel):
    status: str
    processed_students: int
    raised_alerts: int


class RiskPredictionOut(BaseModel):
    student_id: int
    student_name: str
    usn: str
    current_percentage: float
    predicted_probability_drop: float
    risk_level: str


class ChatbotRequest(BaseModel):
    question: str


class ChatbotResponse(BaseModel):
    answer: str
