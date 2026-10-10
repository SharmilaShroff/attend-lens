"""
General-Purpose Generative AI Chatbot Service for Attend Lens.
Powered by OpenRouter API via openrouter_client helper.
"""
from typing import Optional
from sqlalchemy.orm import Session
from app.models.models import Student, Attendance, Subject, AttendanceStatus, Alert, ClassRoom
from app.config import get_settings
from app.services.openrouter_client import call_openrouter, is_openrouter_configured

settings = get_settings()


def answer_chatbot_query(db: Session, user_id: int, question: str, student_id: Optional[int] = None) -> str:
    """
    General-purpose AI assistant for Attend Lens.
    Responds to ALL types of queries (general knowledge, study help, writing, coding, advice, casual chat).
    Includes real class attendance data as optional context to use when attendance questions are asked.
    """
    if not is_openrouter_configured():
        return "AI features are not configured. Please add OPENROUTER_API_KEY to backend .env"

    context_prompt = ""
    try:
        student = None
        if student_id:
            student = db.query(Student).filter(Student.id == student_id).first()

        if not student:
            student = db.query(Student).first()

        if student:
            classroom = db.query(ClassRoom).filter(ClassRoom.id == student.class_id).first()
            class_name = classroom.name if classroom else "Current Class"
            class_students = db.query(Student).filter(Student.class_id == student.class_id).all()
            subjects = db.query(Subject).filter(Subject.class_id == student.class_id).all()
            sub_map = {s.id: f"{s.name} ({s.code})" for s in subjects}

            student_summaries = []
            for cs in class_students[:30]:
                recs = db.query(Attendance).filter(Attendance.student_id == cs.id).all()
                tot = len(recs)
                att = sum(1 for r in recs if r.status == AttendanceStatus.present)
                pct = (att / tot * 100.0) if tot > 0 else 100.0
                student_summaries.append(f"- {cs.name} ({cs.usn}): Overall {pct:.1f}%")

            focused_student_str = ""
            if student_id:
                f_recs = db.query(Attendance).filter(Attendance.student_id == student_id).all()
                f_tot = len(f_recs)
                f_att = sum(1 for r in f_recs if r.status == AttendanceStatus.present)
                f_pct = (f_att / f_tot * 100.0) if f_tot > 0 else 100.0
                focused_student_str = f"\nFocused Student Context: {student.name} ({student.usn}) - Overall Attendance: {f_pct:.1f}%\n"

            context_prompt = (
                f"\n--- OPTIONAL ATTENDANCE CONTEXT ---\n"
                f"Class: {class_name}, Threshold Cutoff: {settings.ATTENDANCE_THRESHOLD}%\n"
                f"Subjects: {', '.join(sub_map.values())}\n"
                + focused_student_str +
                "Class Roster Summary:\n" + "\n".join(student_summaries) + "\n"
                f"-----------------------------------\n\n"
            )
    except Exception as e:
        print(f"[Chatbot Context Error] {e}")

    system_prompt = (
        "You are Attend Lens AI Assistant, a friendly, intelligent, and versatile general-purpose AI assistant.\n"
        "You respond helpfully to ALL types of user questions and prompts, including general knowledge, study guidance, "
        "writing help, coding assistance, problem-solving, advice, casual chat, and student academic performance.\n"
        "If the user asks about attendance, subject averages, exam eligibility, or class statistics, use the provided "
        "Optional Attendance Context to give accurate answers. For all other general topics, answer freely and knowledgeably "
        "without restricting your responses to attendance."
    )

    full_user_prompt = f"{context_prompt}User Question: {question}"

    res, err = call_openrouter(full_user_prompt, system_prompt=system_prompt, json_mode=False, timeout_seconds=15)

    if err:
        return f"AI Service Notice: {err}"
    if res:
        return str(res)

    return "Couldn't generate a reply, please try again."

