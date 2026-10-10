"""FastAPI entrypoint for Rollcall - AI Attendance Pattern Analyzer."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import engine, Base
from app.scheduler import start_scheduler
from app.routers import (
    auth, mentor, teacher, student, alerts, remarks, counselling,
    interventions, analytics, chatbot, ml_counsel, absence_followup
)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure database tables exist
    Base.metadata.create_all(bind=engine)
    # Start APScheduler background job for 24h escalation
    scheduler = start_scheduler()
    yield
    if scheduler and scheduler.running:
        scheduler.shutdown()


app = FastAPI(
    title="Rollcall - AI Attendance Pattern Analyzer",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",")] if settings.CORS_ORIGINS else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(mentor.router)
app.include_router(teacher.router)
app.include_router(student.router)
app.include_router(alerts.router)
app.include_router(remarks.router)
app.include_router(counselling.router)
app.include_router(interventions.router)
app.include_router(analytics.router)
app.include_router(chatbot.router)
app.include_router(ml_counsel.router)
app.include_router(absence_followup.router)



@app.get("/", tags=["meta"])
def root():
    return {
        "name": "Attend Lens - Academic Attendance Analyzer API",
        "status": "online",
        "docs_url": "/docs"
    }


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok", "app": "Rollcall AI Attendance Pattern Analyzer"}


@app.get("/api/ai/health", tags=["meta"])
def ai_health():
    """Diagnostic route testing OpenRouter configuration and connectivity."""
    from app.services.openrouter_client import check_openrouter_health
    return check_openrouter_health()

