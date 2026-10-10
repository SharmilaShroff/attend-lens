"""
Grounded AI Chatbot Service for Attend Lens.
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
    Answers chatbot queries strictly using real class attendance data from DB.
    If student_id is provided, includes that student's details as focused context.
    """
    if not is_openrouter_configured():
        return "AI features are not configured. Please add OPENROUTER_API_KEY to backend .env"

    # Find relevant class
    student = None
    if student_id:
        student = db.query(Student).filter(Student.id == student_id).first()

    if not student:
        # Fallback to first available student/class
        student = db.query(Student).first()

    if not student:
        return "No class or student attendance data available in database."

    classroom = db.query(ClassRoom).filter(ClassRoom.id == student.class_id).first()
    class_name = classroom.name if classroom else "Current Class"

    # Fetch all students in class
    class_students = db.query(Student).filter(Student.class_id == student.class_id).all()
    subjects = db.query(Subject).filter(Subject.class_id == student.class_id).all()
    sub_map = {s.id: f"{s.name} ({s.code})" for s in subjects}

    # Summary of all students in class
    student_summaries = []
    for cs in class_students:
        recs = db.query(Attendance).filter(Attendance.student_id == cs.id).all()
        tot = len(recs)
        att = sum(1 for r in recs if r.status == AttendanceStatus.present)
        pct = (att / tot * 100.0) if tot > 0 else 100.0

        # Sub breakdowns
        sub_pcts = []
        for s in subjects:
            s_recs = [r for r in recs if r.subject_id == s.id]
            s_tot = len(s_recs)
            s_att = sum(1 for r in s_recs if r.status == AttendanceStatus.present)
            s_pct = (s_att / s_tot * 100.0) if s_tot > 0 else 100.0
            sub_pcts.append(f"{s.code}: {s_pct:.1f}%")

        student_summaries.append(
            f"- {cs.name} (USN: {cs.usn}): Overall {pct:.1f}% [{', '.join(sub_pcts)}]"
        )

    focused_student_str = ""
    if student_id:
        focus_student = db.query(Student).filter(Student.id == student_id).first()
        if focus_student:
            f_recs = db.query(Attendance).filter(Attendance.student_id == student_id).all()
            f_tot = len(f_recs)
            f_att = sum(1 for r in f_recs if r.status == AttendanceStatus.present)
            f_pct = (f_att / f_tot * 100.0) if f_tot > 0 else 100.0
            focused_student_str = f"\nFOCUSED STUDENT CONTEXT:\nName: {focus_student.name} (USN: {focus_student.usn}), Overall Attendance: {f_pct:.1f}%\n"

    context_prompt = (
        f"CLASS DATA ({class_name}):\n"
        f"Attendance Threshold Cutoff: {settings.ATTENDANCE_THRESHOLD}%\n"
        f"Total Students: {len(class_students)}\n"
        f"Subjects: {', '.join(sub_map.values())}\n"
        + focused_student_str +
        "ROSTER DATA:\n" +
        "\n".join(student_summaries[:35])  # Cap at 35 students to stay well within token limits
    )

    system_prompt = (
        "You are Attend Lens AI Assistant. Answer the user's question accurately using ONLY the provided real class attendance data. "
        "Do NOT invent any student data or numbers not present in the prompt. If the data does not contain the answer, "
        "explicitly state 'I do not have enough data to answer that based on the class records.' "
        "Answer questions like 'Who is below 50%?', 'Which subject has lowest average?', 'Compare Student A and Student B', "
        "'What should I tell mentor about student X?', 'Is he eligible for the exam?'. Keep answers short, clear, and use bullet points or markdown tables when helpful."
    )

    full_user_prompt = f"{context_prompt}\n\nUser Question: {question}"

    res, err = call_openrouter(full_user_prompt, system_prompt=system_prompt, json_mode=False, timeout_seconds=12)

    if err:
        return f"AI Service Notice: {err}"
    if res:
        return str(res)

    return "Unable to process AI chatbot query. Please try again."
