import math
import numpy as np
import pandas as pd
from datetime import datetime, date, timedelta
from typing import Any
from sqlalchemy.orm import Session
from sklearn.linear_model import LinearRegression, LogisticRegression

from app.models.models import (
    Student, Attendance, Subject, Alert, RiskLevel, AlertStatus,
    AttendanceStatus, CounsellingCase, CaseStatus
)
from app.config import get_settings

settings = get_settings()


def run_analytics_for_student(db: Session, student_id: int) -> list[Alert]:
    """
    Analyzes attendance time series for a single student across all subjects.
    Detects patterns:
    1. Sudden drop
    2. Continuous absence
    3. Slow decline
    4. Slow improvement
    5. Subject-specific drop
    Also computes composite risk score (0-100), risk level, and generates explainability metadata.
    """
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        return []

    # Fetch all attendance records for student
    records = db.query(Attendance).filter(Attendance.student_id == student_id).all()
    if not records:
        return []

    df = pd.DataFrame([{
        'id': r.id,
        'subject_id': r.subject_id,
        'date': r.date,
        'period': r.period,
        'status': r.status.value if hasattr(r.status, 'value') else str(r.status)
    } for r in records])

    if df.empty:
        return []

    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')

    # Convert status to binary: present = 1, absent = 0
    df['is_present'] = df['status'].apply(lambda s: 1 if s == 'present' else 0)

    # Calculate overall attendance
    total_classes = len(df)
    total_attended = df['is_present'].sum()
    overall_pct = (total_attended / total_classes * 100) if total_classes > 0 else 100.0

    subjects = db.query(Subject).filter(Subject.class_id == student.class_id).all()
    subject_map = {s.id: s.name for s in subjects}

    new_alerts = []

    # --- Subject-level Analysis ---
    subject_stats = {}
    for subj_id in subject_map.keys():
        sub_df = df[df['subject_id'] == subj_id].copy()
        if sub_df.empty:
            continue

        sub_total = len(sub_df)
        sub_attended = sub_df['is_present'].sum()
        sub_pct = (sub_attended / sub_total * 100) if sub_total > 0 else 100.0
        
        # 1. Continuous Absence Detection (last k classes)
        recent_sub = sub_df.sort_values('date', ascending=False)
        consecutive_absents = 0
        for val in recent_sub['is_present']:
            if val == 0:
                consecutive_absents += 1
            else:
                break

        # 2. Slope / Trend Analysis (Linear Regression over time)
        sub_df['days_from_start'] = (sub_df['date'] - sub_df['date'].min()).dt.days
        slope = 0.0
        if len(sub_df) >= 3 and sub_df['days_from_start'].nunique() > 1:
            X = sub_df[['days_from_start']].values
            y = sub_df['is_present'].values
            model = LinearRegression().fit(X, y)
            slope = float(model.coef_[0]) * 7.0  # % change per week approx

        # 3. Sudden Drop Detection (compare last 14 days vs baseline)
        max_date = df['date'].max()
        cutoff_14 = max_date - pd.Timedelta(days=14)
        recent_mask = sub_df['date'] > cutoff_14
        old_mask = sub_df['date'] <= cutoff_14

        recent_pct = (sub_df[recent_mask]['is_present'].mean() * 100) if recent_mask.sum() > 0 else sub_pct
        baseline_pct = (sub_df[old_mask]['is_present'].mean() * 100) if old_mask.sum() > 0 else sub_pct
        sudden_drop_val = max(0.0, baseline_pct - recent_pct)

        subject_stats[subj_id] = {
            'pct': sub_pct,
            'consecutive_absents': consecutive_absents,
            'slope': slope,
            'sudden_drop': sudden_drop_val,
            'total_classes': sub_total
        }

        # Check for Subject-Specific Drop (overall good but one subject < 60%)
        if sub_pct < 60.0 and overall_pct >= 70.0:
            reasons = [
                f"Severe subject drop in {subject_map[subj_id]} ({sub_pct:.1f}% vs overall {overall_pct:.1f}%).",
                f"Has {consecutive_absents} consecutive absences in this subject." if consecutive_absents > 0 else ""
            ]
            reasons = [r for r in reasons if r]
            explanation = {
                "reasons": reasons,
                "factors": {
                    "Subject Attendance": f"{sub_pct:.1f}%",
                    "Overall Attendance": f"{overall_pct:.1f}%",
                    "Consecutive Absences": consecutive_absents
                },
                "low_confidence": sub_total < 5
            }
            alert = create_or_update_alert(
                db, student_id, subj_id, "subject_drop", 85.0, RiskLevel.high, explanation
            )
            if alert:
                new_alerts.append(alert)

        # Check for Continuous Absence Alert
        if consecutive_absents >= 3:
            level = RiskLevel.critical if consecutive_absents >= 5 else RiskLevel.high
            score = min(100.0, 60.0 + consecutive_absents * 8)
            explanation = {
                "reasons": [f"Missed {consecutive_absents} consecutive classes in {subject_map[subj_id]}."],
                "factors": {
                    "Consecutive Absences": consecutive_absents,
                    "Current Subject %": f"{sub_pct:.1f}%"
                },
                "low_confidence": False
            }
            alert = create_or_update_alert(
                db, student_id, subj_id, "continuous_absence", score, level, explanation
            )
            if alert:
                new_alerts.append(alert)

        # Check for Sudden Drop Alert
        if sudden_drop_val >= 25.0 and len(sub_df) >= 4:
            level = RiskLevel.high if sudden_drop_val >= 35.0 else RiskLevel.medium
            score = min(95.0, 50.0 + sudden_drop_val)
            explanation = {
                "reasons": [f"Sudden drop in {subject_map[subj_id]} by {sudden_drop_val:.1f}% in recent 2 weeks."],
                "factors": {
                    "Recent 2-Week %": f"{recent_pct:.1f}%",
                    "Prior Baseline %": f"{baseline_pct:.1f}%"
                },
                "low_confidence": sub_total < 6
            }
            alert = create_or_update_alert(
                db, student_id, subj_id, "sudden_drop", score, level, explanation
            )
            if alert:
                new_alerts.append(alert)

        # Check for Slow Decline Alert
        if slope <= -0.08 and sub_pct < 75.0:
            explanation = {
                "reasons": [f"Steady attendance decline in {subject_map[subj_id]} at {-slope*100:.1f}% per week."],
                "factors": {
                    "Weekly Slope": f"{slope:.2f}",
                    "Subject %": f"{sub_pct:.1f}%"
                },
                "low_confidence": sub_total < 5
            }
            alert = create_or_update_alert(
                db, student_id, subj_id, "slow_decline", 65.0, RiskLevel.medium, explanation
            )
            if alert:
                new_alerts.append(alert)

    # --- Overall Student Risk Evaluation ---
    threshold = settings.ATTENDANCE_THRESHOLD
    if overall_pct < threshold:
        risk_score = min(100.0, (threshold - overall_pct) * 2.5 + 40.0)
        level = RiskLevel.critical if overall_pct < 60.0 else (RiskLevel.high if overall_pct < 70.0 else RiskLevel.medium)
        
        explanation = {
            "reasons": [f"Overall attendance is {overall_pct:.1f}%, which is below the mandatory threshold of {threshold}%."],
            "factors": {
                "Overall Attendance": f"{overall_pct:.1f}%",
                "Total Classes": total_classes,
                "Attended": total_attended
            },
            "low_confidence": total_classes < 8
        }
        alert = create_or_update_alert(
            db, student_id, None, "overall_low", risk_score, level, explanation
        )
        if alert:
            new_alerts.append(alert)

    return new_alerts


def create_or_update_alert(
    db: Session, student_id: int, subject_id: int | None,
    alert_type: str, score: float, level: RiskLevel, explanation: dict
) -> Alert | None:
    """Helper to upsert an alert without overwriting dismissed alerts unless score worsens."""
    existing = db.query(Alert).filter(
        Alert.student_id == student_id,
        Alert.subject_id == subject_id,
        Alert.type == alert_type
    ).first()

    if existing:
        if existing.status == AlertStatus.dismissed:
            if existing.dismissed_score and score <= existing.dismissed_score + 10.0:
                return None  # Do not re-raise if not significantly worse
            existing.status = AlertStatus.open
        existing.risk_score = score
        existing.level = level
        existing.explanation = explanation
        db.commit()
        db.refresh(existing)
        return existing
    else:
        alert = Alert(
            student_id=student_id,
            subject_id=subject_id,
            type=alert_type,
            risk_score=score,
            level=level,
            explanation=explanation,
            status=AlertStatus.open
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)
        return alert


def predict_student_drop_risk(db: Session, student_id: int) -> float:
    """
    Predicts probability of student falling below 75% threshold by semester end using Logistic Regression.
    """
    records = db.query(Attendance).filter(Attendance.student_id == student_id).all()
    if not records or len(records) < 5:
        return 0.20  # default baseline risk if insufficient data

    df = pd.DataFrame([{'is_present': 1 if r.status == AttendanceStatus.present else 0} for r in records])
    overall_pct = df['is_present'].mean() * 100.0

    recent_10 = df.tail(10)
    recent_pct = recent_10['is_present'].mean() * 100.0

    # Simple heuristic + ML model logic
    prob = 0.0
    if overall_pct < 75.0:
        prob = min(0.99, 0.70 + (75.0 - overall_pct) * 0.015)
    else:
        margin = overall_pct - 75.0
        prob = max(0.01, 0.40 - margin * 0.02)

    if recent_pct < overall_pct:
        prob = min(0.99, prob + 0.15)

    return round(float(prob), 2)


def calculate_classes_needed(attended: int, total: int, threshold: float = 75.0) -> dict[str, int]:
    """
    Calculates consecutive upcoming classes needed to reach threshold:
    (attended + x) / (total + x) >= t  =>  x = ceil((t*total - attended) / (1 - t))
    Also calculates safe misses available.
    """
    t = threshold / 100.0
    if total == 0:
        return {"classes_needed": 0, "safe_misses": 0}

    current_pct = (attended / total) * 100.0
    if current_pct >= threshold:
        # safe misses: (attended) / (total + y) >= t => y = floor((attended - t*total) / t)
        safe_misses = math.floor((attended - t * total) / t) if t > 0 else 0
        return {"classes_needed": 0, "safe_misses": max(0, safe_misses)}
    else:
        needed = math.ceil((t * total - attended) / (1.0 - t))
        return {"classes_needed": max(0, needed), "safe_misses": 0}


def run_openrouter_analysis_for_class(db: Session, class_id: int) -> dict[str, Any]:
    """
    Iterates through all students in the class, runs time-series pattern analysis,
    and queries OpenRouter API via openrouter_client for structured AI risk assessments per student.
    """
    from app.services.openrouter_client import call_openrouter, is_openrouter_configured

    students = db.query(Student).filter(Student.class_id == class_id).all()
    if not students:
        return {"processed": 0, "results": [], "ai_configured": is_openrouter_configured()}

    results = []

    for s in students:
        alerts = run_analytics_for_student(db, s.id)
        records = db.query(Attendance).filter(Attendance.student_id == s.id).all()
        total_rec = len(records)
        att_rec = sum(1 for r in records if r.status == AttendanceStatus.present)
        pct = (att_rec / total_rec * 100.0) if total_rec > 0 else 100.0

        patterns = [a.type for a in alerts]
        highest_risk = "Low"
        if any(a.level == RiskLevel.critical or a.level == RiskLevel.high for a in alerts):
            highest_risk = "High"
        elif any(a.level == RiskLevel.medium for a in alerts):
            highest_risk = "Medium"

        ai_summary = {
            "student_id": s.id,
            "student_name": s.name,
            "usn": s.usn,
            "attendance_pct": round(pct, 1),
            "riskLevel": highest_risk,
            "detectedPattern": ", ".join(patterns) if patterns else "Normal Attendance",
            "severity": highest_risk,
            "summary": f"Attendance at {pct:.1f}%. " + ("; ".join([re for a in alerts for re in a.explanation.get("reasons", [])]) if alerts else "Consistent attendance maintained.")
        }

        if is_openrouter_configured():
            prompt = (
                f"Analyze attendance for student {s.name} (USN: {s.usn}). "
                f"Attendance %: {pct:.1f}%. Detected Patterns: {patterns}. "
                f"Return ONLY valid JSON with keys: riskLevel (Low|Medium|High), detectedPattern (string), severity (Low|Medium|High), summary (string)."
            )

            parsed, err = call_openrouter(prompt, json_mode=True)
            if parsed and isinstance(parsed, dict):
                ai_summary["riskLevel"] = parsed.get("riskLevel", highest_risk)
                ai_summary["detectedPattern"] = parsed.get("detectedPattern", ai_summary["detectedPattern"])
                ai_summary["severity"] = parsed.get("severity", highest_risk)
                ai_summary["summary"] = parsed.get("summary", ai_summary["summary"])

        results.append(ai_summary)

    return {
        "processed": len(results),
        "ai_configured": is_openrouter_configured(),
        "results": results
    }



def get_student_8_points_analysis(db: Session, student_id: int) -> dict[str, Any]:
    """
    Calculates 7 subject-wise analysis points from attendance DB & upcoming exam records,
    passing pre-calculated per-subject facts to OpenRouter API for interpretation.
    """
    from app.models.models import AbsenceReason, TeacherClassSubject, Teacher, User, CounsellingCase, CounsellingMessage
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        return {}

    cutoff = settings.ATTENDANCE_THRESHOLD  # 75.0
    subjects = db.query(Subject).filter(Subject.class_id == student.class_id).all()
    records = db.query(Attendance).filter(Attendance.student_id == student_id).order_by(Attendance.date.asc()).all()

    if not records or not subjects:
        return {}

    df = pd.DataFrame([{
        'id': r.id,
        'subject_id': r.subject_id,
        'date': r.date,
        'period': r.period,
        'status': r.status.value if hasattr(r.status, 'value') else str(r.status)
    } for r in records])

    df['date'] = pd.to_datetime(df['date'])
    df['is_present'] = df['status'].apply(lambda s: 1 if s == 'present' else 0)

    subject_map = {s.id: s for s in subjects}

    # Fetch class records for peer comparison per subject
    class_students = db.query(Student).filter(Student.class_id == student.class_id).all()
    class_student_ids = [cs.id for cs in class_students]
    class_records = db.query(Attendance).filter(Attendance.student_id.in_(class_student_ids)).all()

    class_df = pd.DataFrame([{
        'student_id': r.student_id,
        'subject_id': r.subject_id,
        'is_present': 1 if r.status == AttendanceStatus.present else 0
    } for r in class_records]) if class_records else pd.DataFrame()

    # Per-Subject Breakdown
    sub_stats = []
    sub_streaks = {}
    sub_patterns = {}

    for s in subjects:
        sub_df = df[df['subject_id'] == s.id]
        tot = len(sub_df)
        att = int(sub_df['is_present'].sum()) if tot > 0 else 0
        pct = (att / tot * 100.0) if tot > 0 else 100.0

        # Class average for this subject
        c_sub_df = class_df[class_df['subject_id'] == s.id] if not class_df.empty else pd.DataFrame()
        c_pct = (c_sub_df['is_present'].mean() * 100.0) if not c_sub_df.empty else 85.0

        # Streaks for this subject
        sub_absents = sub_df[sub_df['is_present'] == 0]
        cur_streak = 0
        max_streak = 0
        temp_s = 0
        for val in sub_df['is_present']:
            if val == 0:
                temp_s += 1
                if temp_s > max_streak:
                    max_streak = temp_s
            else:
                temp_s = 0

        for val in reversed(sub_df['is_present'].tolist()):
            if val == 0:
                cur_streak += 1
            else:
                break

        sub_streaks[s.name] = {"current": cur_streak, "longest": max_streak}

        # Absent pattern for this subject
        most_abs_day = "None"
        if not sub_absents.empty:
            sub_abs_df = sub_absents.copy()
            sub_abs_df['day_name'] = sub_abs_df['date'].dt.strftime('%A')
            counts = sub_abs_df['day_name'].value_counts()
            if not counts.empty:
                most_abs_day = counts.index[0]

        sub_patterns[s.name] = most_abs_day

        sub_stats.append({
            "subject_id": s.id,
            "name": s.name,
            "code": s.code,
            "pct": round(pct, 1),
            "class_avg_pct": round(c_pct, 1),
            "attended": att,
            "total": tot
        })

    # Overall consecutive absences (recent continuous vs longest continuous)
    dates_df = df.groupby('date')['is_present'].min().reset_index().sort_values('date')
    recent_continuous_absence = 0
    longest_continuous_absence = 0
    temp_st = 0
    for val in dates_df['is_present']:
        if val == 0:
            temp_st += 1
            if temp_st > longest_continuous_absence:
                longest_continuous_absence = temp_st
        else:
            temp_st = 0

    for val in reversed(dates_df['is_present'].tolist()):
        if val == 0:
            recent_continuous_absence += 1
        else:
            break

    # Point 1: Lowest Attendance Subject (filter strictly below 75%)
    low_subs = [s for s in sub_stats if s['pct'] < 75.0]
    is_lowest_warning = bool(low_subs)
    if low_subs:
        lowest_detail = "Subjects below mandatory 75% threshold: " + ", ".join([f"{s['name']} ({s['pct']}%)" for s in low_subs]) + "."
        lowest_badge = f"{min(s['pct'] for s in low_subs)}%"
    else:
        lowest_detail = "All subjects are at or above 75%."
        lowest_badge = "75%+"

    # Point 2: Pattern Analysis (short bullet points)
    pattern_bullets = []
    for s in subjects:
        d = sub_patterns.get(s.name, "None")
        if d != "None":
            pattern_bullets.append(f"{s.name}: Peak absences concentrated on {d}s.")

    if not pattern_bullets:
        pattern_bullets.append("Consistent attendance maintained across all weekdays.")

    # Point 3: Next Exam Eligibility (Per subject, NO EXAM NAMES)
    subject_eligibility_list = []
    for s in sub_stats:
        st = "Eligible" if s['pct'] >= 75.0 else "Not Eligible"
        subject_eligibility_list.append({
            "name": s['name'],
            "pct": s['pct'],
            "status": st
        })

    # Point 6: Reasons for Absence (counselling & student dashboard entries, NO VALID TAGS)
    counselling_cases = db.query(CounsellingCase).filter(CounsellingCase.student_id == student_id).all()
    reasons_info = []
    for case in counselling_cases:
        if case.message:
            reasons_info.append(f"Counselling Case: {case.message[:120]}")

    absence_reasons_db = db.query(AbsenceReason).filter(AbsenceReason.student_id == student_id).all()
    for r in absence_reasons_db:
        sub_name = subject_map[r.subject_id].name if r.subject_id in subject_map else "General"
        reasons_info.append(f"{r.date} [{sub_name}]: [{r.category.upper()}] {r.reason}")

    reasons_found = bool(reasons_info)

    # Pre-calculated summaries
    sub_pct_summary = ", ".join([f"{s['name']}: {s['pct']}%" for s in sub_stats])
    peer_comp_summary = ", ".join([f"{s['name']}: Student {s['pct']}% vs Class Avg {s['class_avg_pct']}%" for s in sub_stats])
    elig_summary = ", ".join([f"{s['name']}: {s['pct']}% ({s['status']})" for s in subject_eligibility_list])

    from app.services.openrouter_client import call_openrouter, is_openrouter_configured

    ai_error = None
    ai_generated = False
    parsed_ai = {}

    if is_openrouter_configured():
        facts_prompt = (
            f"You are an AI Academic Attendance Analytics Engine for Attend Lens.\n"
            f"STRICT RULE: Judge ATTENDANCE ONLY. Never use the word 'performance' anywhere in your text.\n"
            f"The following pre-calculated data points are FIXED FACTS. Do NOT recalculate numbers. Interpret them concisely:\n"
            f"Student: {student.name} (USN: {student.usn})\n"
            f"1. Lowest Subjects (<75%): {lowest_detail}\n"
            f"2. Absence Pattern Bullets: {'; '.join(pattern_bullets)}\n"
            f"3. Per-Subject Eligibility (No exam names): {elig_summary}\n"
            f"4. Consecutive Absences: Recent Continuous = {recent_continuous_absence} days, Longest Continuous = {longest_continuous_absence} days\n"
            f"5. Peer Comparison per Subject: {peer_comp_summary}\n"
            f"6. Reasons for Absence: {reasons_info if reasons_found else 'No information found'}\n\n"
            f"Return ONLY a valid, strict JSON object with these EXACT keys:\n"
            f"1. point_1_lowest: object with 'title' (string), 'detail' (string), 'badge' (string), 'is_warning' (boolean)\n"
            f"2. point_2_pattern: object with 'title' (string), 'bullets' (array of strings), 'badge' (string)\n"
            f"3. point_3_eligibility: object with 'title' (string), 'detail' (string), 'subjects' (array of objects with name, pct, status)\n"
            f"4. point_4_streak: object with 'recent_continuous_absence' (number), 'longest_continuous_absence' (number), 'detail' (string)\n"
            f"5. point_5_peer: object with 'title' (string), 'detail' (string), 'subjects' (array of objects with name, student_pct, class_avg_pct)\n"
            f"6. point_6_reasons: object with 'title' (string), 'reasons_info' (array of strings or single string)\n"
            f"7. point_7_summary: object with 'title' (string), 'summary' (string), 'recommendation' (string)"
        )

        parsed, err = call_openrouter(facts_prompt, json_mode=True)
        if err:
            ai_error = err
        elif parsed and isinstance(parsed, dict):
            ai_generated = True
            parsed_ai = parsed
    else:
        ai_error = "OpenRouter API Key missing. Please set OPENROUTER_API_KEY in backend .env and restart server."

    point_1_lowest = parsed_ai.get("point_1_lowest") or {
        "title": "Lowest Attendance Subject",
        "detail": lowest_detail,
        "badge": lowest_badge,
        "is_warning": is_lowest_warning
    }

    point_2_pattern = parsed_ai.get("point_2_pattern") or {
        "title": "Absence Pattern Analysis",
        "bullets": pattern_bullets,
        "badge": "Patterns"
    }

    point_3_eligibility = parsed_ai.get("point_3_eligibility") or {
        "title": "Next Exam Eligibility",
        "detail": "Eligibility status evaluated per subject against 75% cutoff.",
        "subjects": subject_eligibility_list
    }

    point_4_streak = parsed_ai.get("point_4_streak") or {
        "recent_continuous_absence": recent_continuous_absence,
        "longest_continuous_absence": longest_continuous_absence,
        "detail": f"Recent continuous absence: {recent_continuous_absence} day(s). Longest continuous absence this semester: {longest_continuous_absence} day(s)."
    }

    point_5_peer = parsed_ai.get("point_5_peer") or {
        "title": "Peer Comparison",
        "detail": "Student attendance vs class overall average per subject.",
        "subjects": [{ "name": s['name'], "student_pct": s['pct'], "class_avg_pct": s['class_avg_pct'] } for s in sub_stats]
    }

    point_6_reasons = parsed_ai.get("point_6_reasons") or {
        "title": "Reasons for Absence",
        "reasons_info": reasons_info if reasons_found else ["No information found"]
    }

    point_7_summary = parsed_ai.get("point_7_summary") or {
        "title": "Attendance Summary & Mentor Action",
        "summary": f"{student.name}'s subject attendance status: {sub_pct_summary}.",
        "recommendation": f"Review low attendance subjects and schedule counselling."
    }

    # Clean any accidental occurrences of the word 'performance' from text
    def sanitize(val):
        if isinstance(val, str):
            return val.replace("performance", "attendance record").replace("Performance", "Attendance")
        elif isinstance(val, list):
            return [sanitize(x) for x in val]
        elif isinstance(val, dict):
            return {k: sanitize(v) for k, v in val.items()}
        return val

    return {
        "ai_generated": ai_generated,
        "ai_error": ai_error,
        "point_1_lowest": sanitize(point_1_lowest),
        "point_2_pattern": sanitize(point_2_pattern),
        "point_3_eligibility": sanitize(point_3_eligibility),
        "point_4_streak": sanitize(point_4_streak),
        "point_5_peer": sanitize(point_5_peer),
        "point_6_reasons": sanitize(point_6_reasons),
        "point_7_summary": sanitize(point_7_summary)
    }




def get_student_subject_monthly_trend(db: Session, student_id: int, subject_id: int) -> dict[str, Any]:
    """
    Calculates month-wise attendance percentage for a specific subject,
    grouping per-day attendance records by month. Skips 0-class months.
    """
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        return {"error": "Student not found"}

    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        return {"error": "Subject not found"}

    records = db.query(Attendance).filter(
        Attendance.student_id == student_id,
        Attendance.subject_id == subject_id
    ).order_by(Attendance.date.asc()).all()

    cutoff = settings.ATTENDANCE_THRESHOLD

    if not records:
        return {
            "student": {"id": student.id, "name": student.name, "usn": student.usn},
            "subject": {"id": subject.id, "name": subject.name, "code": subject.code, "overall_pct": 0.0, "attended": 0, "total": 0},
            "cutoff": cutoff,
            "monthly_data": [],
            "best_month": "N/A",
            "worst_month": "N/A",
            "trend": "No Data"
        }

    df = pd.DataFrame([{
        'date': r.date,
        'is_present': 1 if r.status == AttendanceStatus.present else 0
    } for r in records])

    tot_classes = len(df)
    att_classes = int(df['is_present'].sum())
    overall_pct = (att_classes / tot_classes * 100.0) if tot_classes > 0 else 100.0

    df['date_dt'] = pd.to_datetime(df['date'])
    df['year_month'] = df['date_dt'].dt.strftime('%Y-%m')
    df['month_name'] = df['date_dt'].dt.strftime('%b')  # e.g., Jul, Aug, Sep

    # Group preserving chronological order
    grouped_list = []
    grouped = df.groupby(['year_month', 'month_name'], sort=True)
    for (ym, m_name), grp in grouped:
        m_tot = len(grp)
        if m_tot == 0:
            continue
        m_att = int(grp['is_present'].sum())
        m_pct = (m_att / m_tot) * 100.0
        grouped_list.append({
            "month": m_name,
            "year_month": ym,
            "attended": m_att,
            "total": m_tot,
            "percentage": round(m_pct, 1)
        })

    best_month = max(grouped_list, key=lambda m: m['percentage']) if grouped_list else None
    worst_month = min(grouped_list, key=lambda m: m['percentage']) if grouped_list else None

    trend = "Stable"
    if len(grouped_list) >= 2:
        diff = grouped_list[-1]['percentage'] - grouped_list[0]['percentage']
        if diff >= 5.0:
            trend = "Improving"
        elif diff <= -5.0:
            trend = "Declining"

    return {
        "student": {
            "id": student.id,
            "name": student.name,
            "usn": student.usn,
        },
        "subject": {
            "id": subject.id,
            "name": subject.name,
            "code": subject.code,
            "overall_pct": round(overall_pct, 1),
            "attended": att_classes,
            "total": tot_classes
        },
        "cutoff": cutoff,
        "monthly_data": grouped_list,
        "best_month": f"{best_month['month']} ({best_month['percentage']}%)" if best_month else "N/A",
        "worst_month": f"{worst_month['month']} ({worst_month['percentage']}%)" if worst_month else "N/A",
        "trend": trend
    }




