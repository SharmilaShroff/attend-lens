"""
Export SQLite database (attendance.db) into a standalone, ready-to-import MySQL .sql dump file (attendlens_dump.sql).
"""
import os
import json
from datetime import datetime, date
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.models import (
    User, Mentor, Teacher, ClassRoom, Student, Subject, TeacherClassSubject,
    Attendance, AttendanceAuditLog, Remark, AbsenceReason, Alert,
    CounsellingCase, CounsellingMessage, Intervention, ChatbotLog, Exam, AbsenceFollowUp, EmailQueue
)

SQLITE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "attendance.db"))
SQLITE_URL = f"sqlite:///{SQLITE_PATH}"
DUMP_SQL_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "attendlens_dump.sql"))


def escape_mysql_val(val):
    if val is None:
        return "NULL"
    elif isinstance(val, (int, float)):
        return str(val)
    elif isinstance(val, bool):
        return "1" if val else "0"
    elif isinstance(val, (datetime, date)):
        return f"'{val.strftime('%Y-%m-%d %H:%M:%S')}'" if isinstance(val, datetime) else f"'{val.strftime('%Y-%m-%d')}'"
    elif isinstance(val, (dict, list)):
        dumped = json.dumps(val).replace("\\", "\\\\").replace("'", "''")
        return f"'{dumped}'"
    elif hasattr(val, "value"):  # Enum
        enum_val = str(val.value).replace("\\", "\\\\").replace("'", "''")
        return f"'{enum_val}'"
    else:
        str_val = str(val).replace("\\", "\\\\").replace("'", "''")
        return f"'{str_val}'"


def export_sql():
    print("=" * 60)
    print("EXPORTING SQLITE TO MYSQL DUMP FILE (.sql)")
    print("=" * 60)

    if not os.path.exists(SQLITE_PATH):
        print(f"[ERROR] SQLite database file not found at: {SQLITE_PATH}")
        return

    sqlite_engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=sqlite_engine)
    SqliteSession = sessionmaker(bind=sqlite_engine)
    db = SqliteSession()

    models_to_export = [
        ("users", User),
        ("mentors", Mentor),
        ("teachers", Teacher),
        ("classes", ClassRoom),
        ("subjects", Subject),
        ("teacher_class_subject", TeacherClassSubject),
        ("students", Student),
        ("attendance", Attendance),
        ("attendance_audit_log", AttendanceAuditLog),
        ("remarks", Remark),
        ("absence_reasons", AbsenceReason),
        ("alerts", Alert),
        ("counselling_cases", CounsellingCase),
        ("counselling_messages", CounsellingMessage),
        ("interventions", Intervention),
        ("chatbot_logs", ChatbotLog),
        ("exams", Exam),
        ("absence_followups", AbsenceFollowUp),
        ("email_queue", EmailQueue),
    ]

    sql_lines = []
    sql_lines.append("-- Attend Lens MySQL Database Dump")
    sql_lines.append(f"-- Exported on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    sql_lines.append("CREATE DATABASE IF NOT EXISTS attendlens_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
    sql_lines.append("USE attendlens_db;\n")
    sql_lines.append("SET FOREIGN_KEY_CHECKS = 0;\n")

    # Generate CREATE TABLE schemas from SQLAlchemy Base metadata
    from sqlalchemy.schema import CreateTable
    from sqlalchemy.dialects import mysql

    for table_name, model_cls in models_to_export:
        create_stmt = str(CreateTable(model_cls.__table__).compile(dialect=mysql.dialect()))
        sql_lines.append(f"-- Schema for {table_name}")
        sql_lines.append(f"DROP TABLE IF EXISTS `{table_name}`;")
        sql_lines.append(create_stmt.strip() + ";\n")

    # Generate INSERT statements
    total_records = 0

    for table_name, model_cls in models_to_export:
        records = db.query(model_cls).all()
        count = len(records)
        if count == 0:
            continue

        mapper = inspect(model_cls)
        col_names = [col.key for col in mapper.columns]
        quoted_cols = ", ".join([f"`{col}`" for col in col_names])

        sql_lines.append(f"-- Data for {table_name} ({count} rows)")

        val_rows = []
        for row in records:
            vals = [escape_mysql_val(getattr(row, col)) for col in col_names]
            val_rows.append(f"({', '.join(vals)})")

        # Write INSERT statements in chunks of 50
        chunk_size = 50
        for i in range(0, len(val_rows), chunk_size):
            chunk = val_rows[i:i + chunk_size]
            insert_stmt = f"INSERT INTO `{table_name}` ({quoted_cols}) VALUES\n" + ",\n".join(chunk) + ";"
            sql_lines.append(insert_stmt)

        sql_lines.append("")
        total_records += count
        print(f"  Exported `{table_name}`: {count} rows")

    sql_lines.append("SET FOREIGN_KEY_CHECKS = 1;")
    sql_lines.append("-- Dump completed.")

    with open(DUMP_SQL_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(sql_lines))

    db.close()
    print("-" * 60)
    print(f"[SUCCESS] Exported complete MySQL dump file ({total_records} total rows):")
    print(f"  {DUMP_SQL_PATH}")
    print("=" * 60)


if __name__ == "__main__":
    export_sql()
