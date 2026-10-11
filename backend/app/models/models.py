"""All SQLAlchemy ORM models for the Attendance Pattern Analyzer."""
import enum
from datetime import datetime, date

from sqlalchemy import (
    JSON, Boolean, Date, DateTime, Enum, Float, ForeignKey, Integer, String,
    Text, UniqueConstraint, Index, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# ---------------------------------------------------------------- enums
class Role(str, enum.Enum):
    mentor = "mentor"
    teacher = "teacher"
    student = "student"


class AttendanceStatus(str, enum.Enum):
    present = "present"
    absent = "absent"


class RiskLevel(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class AlertStatus(str, enum.Enum):
    open = "open"
    dismissed = "dismissed"
    resolved = "resolved"


class CaseStatus(str, enum.Enum):
    draft = "draft"                # AI message generated, awaiting mentor review
    sent = "sent"
    responded = "responded"
    escalated = "escalated"        # parents emailed after 24h silence
    resolved = "resolved"


class ReasonStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


def _ts():
    return mapped_column(DateTime, server_default=func.now())


# ---------------------------------------------------------------- identity
class User(Base):
    """Login identity. Staff log in with email; students with USN."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    role: Mapped[Role] = mapped_column(Enum(Role), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str | None] = mapped_column(String(190), unique=True)
    usn: Mapped[str | None] = mapped_column(String(30), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = _ts()


class Mentor(Base):
    __tablename__ = "mentors"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    department: Mapped[str | None] = mapped_column(String(100))

    user: Mapped[User] = relationship()
    classes: Mapped[list["ClassRoom"]] = relationship(back_populates="mentor", cascade="all, delete-orphan")


class Teacher(Base):
    __tablename__ = "teachers"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    department: Mapped[str | None] = mapped_column(String(100))

    user: Mapped[User] = relationship()


# ---------------------------------------------------------------- academics
class ClassRoom(Base):
    __tablename__ = "classes"
    id: Mapped[int] = mapped_column(primary_key=True)
    mentor_id: Mapped[int] = mapped_column(ForeignKey("mentors.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    branch: Mapped[str] = mapped_column(String(60), nullable=False)
    semester: Mapped[int] = mapped_column(Integer, nullable=False)
    section: Mapped[str | None] = mapped_column(String(10))
    academic_year: Mapped[str] = mapped_column(String(15), nullable=False)
    created_at: Mapped[datetime] = _ts()

    mentor: Mapped[Mentor] = relationship(back_populates="classes")
    students: Mapped[list["Student"]] = relationship(back_populates="classroom", cascade="all, delete-orphan")
    subjects: Mapped[list["Subject"]] = relationship(back_populates="classroom", cascade="all, delete-orphan")


class Student(Base):
    __tablename__ = "students"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), unique=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    usn: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(190))
    parent_email: Mapped[str | None] = mapped_column(String(190))
    parent_phone: Mapped[str | None] = mapped_column(String(25))
    created_at: Mapped[datetime] = _ts()

    classroom: Mapped[ClassRoom] = relationship(back_populates="students")
    user: Mapped[User | None] = relationship()


class Subject(Base):
    __tablename__ = "subjects"
    __table_args__ = (UniqueConstraint("class_id", "code", name="uq_subject_class_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    code: Mapped[str] = mapped_column(String(30), nullable=False)

    classroom: Mapped[ClassRoom] = relationship(back_populates="subjects")


class TeacherClassSubject(Base):
    """Teacher <-> (class, subject) mapping. Removing a row never touches the class itself."""
    __tablename__ = "teacher_class_subject"
    __table_args__ = (UniqueConstraint("teacher_id", "class_id", "subject_id", name="uq_tcs"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id", ondelete="CASCADE"), index=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id", ondelete="CASCADE"), index=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id", ondelete="CASCADE"), index=True)
    assigned_by_mentor: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = _ts()


# ---------------------------------------------------------------- attendance
class Attendance(Base):
    """One row per student/subject/date/period. A MISSING row means 'not marked' (never absent/present)."""
    __tablename__ = "attendance"
    __table_args__ = (
        UniqueConstraint("student_id", "subject_id", "date", "period", name="uq_attendance_slot"),
        Index("ix_att_student_date", "student_id", "date"),
        Index("ix_att_subject_date", "subject_id", "date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id", ondelete="CASCADE"), index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    period: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[AttendanceStatus] = mapped_column(Enum(AttendanceStatus), nullable=False)
    marked_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = _ts()
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class AttendanceAuditLog(Base):
    __tablename__ = "attendance_audit_log"
    __table_args__ = (Index("ix_audit_student_date", "student_id", "date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    attendance_id: Mapped[int | None] = mapped_column(ForeignKey("attendance.id", ondelete="SET NULL"))
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"))
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id", ondelete="CASCADE"))
    date: Mapped[date] = mapped_column(Date, nullable=False)
    period: Mapped[int] = mapped_column(Integer, default=1)
    old_status: Mapped[str | None] = mapped_column(String(10))   # NULL = was not marked
    new_status: Mapped[str] = mapped_column(String(10), nullable=False)
    changed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    changed_at: Mapped[datetime] = _ts()
    reason: Mapped[str | None] = mapped_column(String(255))


# ---------------------------------------------------------------- remarks / reasons
class Remark(Base):
    __tablename__ = "remarks"
    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    role: Mapped[Role] = mapped_column(Enum(Role), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = _ts()
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    author: Mapped[User] = relationship()


class AbsenceReason(Base):
    """Student-submitted reason for an absent day. Review does NOT change the attendance record."""
    __tablename__ = "absence_reasons"
    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    subject_id: Mapped[int | None] = mapped_column(ForeignKey("subjects.id", ondelete="SET NULL"))
    date: Mapped[date] = mapped_column(Date, nullable=False)
    category: Mapped[str] = mapped_column(String(30), nullable=False)  # medical/event/personal/other
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    proof_path: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[ReasonStatus] = mapped_column(Enum(ReasonStatus), default=ReasonStatus.pending)
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime)
    review_note: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = _ts()


# ---------------------------------------------------------------- AI alerts
class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (Index("ix_alert_student_status", "student_id", "status"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    subject_id: Mapped[int | None] = mapped_column(ForeignKey("subjects.id", ondelete="CASCADE"), index=True)  # NULL = overall
    type: Mapped[str] = mapped_column(String(40), nullable=False)  # sudden_drop, continuous_absence, slow_decline, subject_drop, ...
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    level: Mapped[RiskLevel] = mapped_column(Enum(RiskLevel), nullable=False)
    explanation: Mapped[dict] = mapped_column(JSON, nullable=False)  # reasons[] + factor contributions + low_confidence
    status: Mapped[AlertStatus] = mapped_column(Enum(AlertStatus), default=AlertStatus.open, index=True)
    override_level: Mapped[RiskLevel | None] = mapped_column(Enum(RiskLevel))
    override_reason: Mapped[str | None] = mapped_column(String(255))
    dismissed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    dismissed_reason: Mapped[str | None] = mapped_column(String(255))
    dismissed_score: Mapped[float | None] = mapped_column(Float)  # score at dismissal; re-raise only if it worsens
    created_at: Mapped[datetime] = _ts()
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


# ---------------------------------------------------------------- counselling
class CounsellingCase(Base):
    __tablename__ = "counselling_cases"
    id: Mapped[int] = mapped_column(primary_key=True)
    alert_id: Mapped[int] = mapped_column(ForeignKey("alerts.id", ondelete="CASCADE"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[CaseStatus] = mapped_column(Enum(CaseStatus), default=CaseStatus.draft, index=True)
    thread_token: Mapped[str] = mapped_column(String(40), unique=True)  # embedded in email subject to map replies
    sent_at: Mapped[datetime | None] = mapped_column(DateTime)
    deadline_at: Mapped[datetime | None] = mapped_column(DateTime, index=True)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime)
    escalated_at: Mapped[datetime | None] = mapped_column(DateTime)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = _ts()

    messages: Mapped[list["CounsellingMessage"]] = relationship(
        back_populates="case", cascade="all, delete-orphan", order_by="CounsellingMessage.created_at")


class CounsellingMessage(Base):
    __tablename__ = "counselling_messages"
    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("counselling_cases.id", ondelete="CASCADE"), index=True)
    sender: Mapped[str] = mapped_column(String(20), nullable=False)    # ai | staff | student | system
    channel: Mapped[str] = mapped_column(String(10), default="app")    # app | email
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = _ts()

    case: Mapped[CounsellingCase] = relationship(back_populates="messages")


class Intervention(Base):
    __tablename__ = "interventions"
    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    alert_id: Mapped[int | None] = mapped_column(ForeignKey("alerts.id", ondelete="SET NULL"))
    staff_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))  # NULL = system action
    type: Mapped[str] = mapped_column(String(40), nullable=False)  # counselling, parent_call, warning_letter, parent_email_auto, ...
    notes: Mapped[str | None] = mapped_column(Text)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    outcome: Mapped[str | None] = mapped_column(String(255))
    attendance_before: Mapped[float | None] = mapped_column(Float)  # % snapshot when logged
    attendance_after: Mapped[float | None] = mapped_column(Float)   # filled in later for before/after comparison
    created_at: Mapped[datetime] = _ts()


class ChatbotLog(Base):
    __tablename__ = "chatbot_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = _ts()


class Exam(Base):
    """Upcoming or scheduled academic examinations for a class."""
    __tablename__ = "exams"
    id: Mapped[int] = mapped_column(primary_key=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    date: Mapped[date | None] = mapped_column(Date)
    subject_ids: Mapped[list] = mapped_column(JSON, nullable=False)  # List of subject IDs covered
    created_at: Mapped[datetime] = _ts()


class FollowUpStatus(str, enum.Enum):
    pending = "pending"
    student_emailed = "student_emailed"
    responded = "responded"
    parent_emailed = "parent_emailed"
    failed = "failed"
    cancelled = "cancelled"


class AbsenceFollowUp(Base):
    """Absence follow-up tracking student email, 24h wait, response detection, and parent escalation."""
    __tablename__ = "absence_followups"
    __table_args__ = (
        UniqueConstraint("student_id", "absence_date", name="uq_student_absence_date"),
        Index("ix_followup_student_date", "student_id", "absence_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    absence_date: Mapped[date] = mapped_column(Date, nullable=False)
    subject_ids: Mapped[list] = mapped_column(JSON, default=list)  # Subject IDs absent on this date
    status: Mapped[FollowUpStatus] = mapped_column(Enum(FollowUpStatus), default=FollowUpStatus.pending, index=True)
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime)
    student_email_sent_at: Mapped[datetime | None] = mapped_column(DateTime)
    parent_email_sent_at: Mapped[datetime | None] = mapped_column(DateTime)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime)
    response_source: Mapped[str | None] = mapped_column(String(50))  # submit_absence | counselling_inbox | email_link
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = _ts()
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    student: Mapped[Student] = relationship()


class QueueRecipientType(str, enum.Enum):
    student = "student"
    parent = "parent"


class QueueStatus(str, enum.Enum):
    pending = "pending"
    sent = "sent"
    failed = "failed"
    skipped = "skipped"


class EmailQueue(Base):
    """Database-backed queue for immediate absence email notifications."""
    __tablename__ = "email_queue"
    __table_args__ = (
        Index("ix_email_queue_student_type_date", "student_id", "recipient_type", "absence_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    recipient_type: Mapped[QueueRecipientType] = mapped_column(Enum(QueueRecipientType), nullable=False)
    recipient_email: Mapped[str | None] = mapped_column(String(190))
    absence_date: Mapped[date] = mapped_column(Date, nullable=False)
    subject_ids: Mapped[list] = mapped_column(JSON, default=list)
    teacher_name: Mapped[str | None] = mapped_column(String(120))
    status: Mapped[QueueStatus] = mapped_column(Enum(QueueStatus), default=QueueStatus.pending, index=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = _ts()
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    student: Mapped[Student] = relationship()




# ---------------------------------------------------------------- n8n notification de-duplication
class N8nNotificationLog(Base):
    """
    Tracks which (student, subject, date, period) combos have already been
    sent through the n8n absence-email webhook, preventing duplicate emails
    when attendance is re-saved or edited.
    """
    __tablename__ = "n8n_notification_log"
    __table_args__ = (
        UniqueConstraint("student_id", "subject_id", "date", "period", name="uq_n8n_notif"),
        Index("ix_n8n_notif_lookup", "subject_id", "date", "period"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id", ondelete="CASCADE"), index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    period: Mapped[int] = mapped_column(Integer, nullable=False)
    notified_at: Mapped[datetime] = _ts()
