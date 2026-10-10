from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.deps import get_current_user
from app.models.models import User, Student, ChatbotLog
from app.services.chatbot import answer_chatbot_query

router = APIRouter(prefix="/chatbot", tags=["chatbot"])


class ChatQuery(BaseModel):
    question: str
    student_id: int | None = None


@router.post("")
def chatbot_message(body: ChatQuery, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    answer = answer_chatbot_query(db, user.id, body.question, student_id=body.student_id)

    # Log interaction if student available
    target_student_id = body.student_id
    if not target_student_id:
        st = db.query(Student).first()
        if st:
            target_student_id = st.id

    if target_student_id:
        try:
            log = ChatbotLog(student_id=target_student_id, question=body.question, answer=answer)
            db.add(log)
            db.commit()
        except Exception:
            pass

    return {"answer": answer}
