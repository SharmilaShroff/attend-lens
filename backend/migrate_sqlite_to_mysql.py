"""
Data Migration Script: SQLite to MySQL for Attend Lens Backend.
Migrates all tables and existing data from attendance.db (SQLite) to MySQL database.

Usage:
    python migrate_sqlite_to_mysql.py [mysql_url]

Examples:
    python migrate_sqlite_to_mysql.py "mysql+pymysql://root:YOUR_PASSWORD@localhost:3306/attendlens_db"
"""
import os
import sys
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker

from app.config import get_settings
from app.database import Base
from app.models.models import (
    User, Mentor, Teacher, ClassRoom, Student, Subject, TeacherClassSubject,
    Attendance, AttendanceAuditLog, Remark, AbsenceReason, Alert,
    CounsellingCase, CounsellingMessage, Intervention, ChatbotLog, Exam, AbsenceFollowUp
)

settings = get_settings()

SQLITE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "attendance.db"))
SQLITE_URL = f"sqlite:///{SQLITE_PATH}"


def migrate(mysql_url: str):
    print("=" * 60)
    print("ATTEND LENS: SQLITE TO MYSQL DATA MIGRATION TOOL")
    print("=" * 60)

    if not os.path.exists(SQLITE_PATH):
        print(f"[ERROR] SQLite database file not found at: {SQLITE_PATH}")
        return False

    print(f"Source (SQLite): {SQLITE_PATH}")
    print(f"Target (MySQL):  {mysql_url}")

    # 1. Connect to SQLite
    sqlite_engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})
    SqliteSession = sessionmaker(bind=sqlite_engine)
    sqlite_db = SqliteSession()

    # 2. Connect to MySQL
    try:
        mysql_engine = create_engine(mysql_url, pool_pre_ping=True)
        # Test connection
        with mysql_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("[SUCCESS] Connected to MySQL server successfully!")
    except Exception as e:
        print(f"[ERROR] Failed to connect to MySQL database at {mysql_url}: {e}")
        print("\nPlease ensure:")
        print("1. Your local MySQL server is running.")
        print("2. Update DATABASE_URL in backend/.env with your MySQL username and password:")
        print("   DATABASE_URL=mysql+pymysql://USERNAME:PASSWORD@localhost:3306/attendlens_db")
        print("3. Ensure the database exists by running: CREATE DATABASE attendlens_db;")
        return False

    # 3. Create all tables in MySQL
    print("\nCreating database schema in MySQL...")
    Base.metadata.create_all(bind=mysql_engine)
    print("[SUCCESS] MySQL database tables created successfully!")

    MysqlSession = sessionmaker(bind=mysql_engine)
    mysql_db = MysqlSession()

    # Ordered list of models by foreign key dependency
    models_to_migrate = [
        ("User", User),
        ("Mentor", Mentor),
        ("Teacher", Teacher),
        ("ClassRoom", ClassRoom),
        ("Subject", Subject),
        ("TeacherClassSubject", TeacherClassSubject),
        ("Student", Student),
        ("Attendance", Attendance),
        ("AttendanceAuditLog", AttendanceAuditLog),
        ("Remark", Remark),
        ("AbsenceReason", AbsenceReason),
        ("Alert", Alert),
        ("CounsellingCase", CounsellingCase),
        ("CounsellingMessage", CounsellingMessage),
        ("Intervention", Intervention),
        ("ChatbotLog", ChatbotLog),
        ("Exam", Exam),
        ("AbsenceFollowUp", AbsenceFollowUp),
    ]

    print("\nMigrating data table by table...")
    print("-" * 60)

    total_migrated = 0

    for model_name, model_cls in models_to_migrate:
        try:
            records = sqlite_db.query(model_cls).all()
            count = len(records)

            if count == 0:
                print(f"  [{model_name:22s}] 0 rows (skipped)")
                continue

            # Disable foreign key checks temporarily for clean bulk insertion
            mysql_db.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))
            mysql_db.commit()

            inserted = 0
            for item in records:
                mapper = inspect(model_cls)
                data_dict = {column.key: getattr(item, column.key) for column in mapper.columns}

                pk_name = mapper.primary_key[0].name
                existing = mysql_db.query(model_cls).filter(getattr(model_cls, pk_name) == data_dict[pk_name]).first()

                if not existing:
                    new_obj = model_cls(**data_dict)
                    mysql_db.add(new_obj)
                    inserted += 1

            mysql_db.commit()
            mysql_db.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))
            mysql_db.commit()

            total_migrated += inserted
            print(f"  [{model_name:22s}] {inserted}/{count} rows migrated successfully.")

        except Exception as ex:
            mysql_db.rollback()
            print(f"  [{model_name:22s}] [ERROR] Migration failed: {ex}")

    sqlite_db.close()
    mysql_db.close()

    print("-" * 60)
    print(f"[SUCCESS] MIGRATION COMPLETE! Total rows migrated to MySQL: {total_migrated}")
    print("=" * 60)
    return True


if __name__ == "__main__":
    mysql_conn = sys.argv[1] if len(sys.argv) > 1 else settings.DATABASE_URL
    migrate(mysql_conn)
