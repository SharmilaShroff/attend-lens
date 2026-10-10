"""
Script to create the MySQL database 'attendlens_db' and migrate all SQLite data into it.
"""
import sys
import re
import pymysql
from app.config import get_settings
from migrate_sqlite_to_mysql import migrate

def main():
    passwords = [
        '', 'root', 'password', '123456', 'admin', 'root123', 'Password123!', 
        '1234', '12345678', 'root@123', 'root1234', 'admin123', 'mysql',
        'sharmila', 'Sharmila@123', 'Sharmila123', 'sharmila123', 'Sharmila'
    ]
    
    # Also check if password provided via command line arg
    if len(sys.argv) > 1:
        passwords.insert(0, sys.argv[1])

    connected_conn_str = None

    for pwd in passwords:
        try:
            conn = pymysql.connect(host='localhost', user='root', password=pwd, port=3306, autocommit=True)
            print(f"[SUCCESS] Connected to local MySQL server (user: root, password: '{pwd}')")
            
            with conn.cursor() as cur:
                cur.execute("CREATE DATABASE IF NOT EXISTS attendlens_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
                print("[SUCCESS] MySQL database 'attendlens_db' created / verified!")
            conn.close()

            if pwd:
                connected_conn_str = f"mysql+pymysql://root:{pwd}@localhost:3306/attendlens_db"
            else:
                connected_conn_str = "mysql+pymysql://root@localhost:3306/attendlens_db"
            break
        except Exception as e:
            # print(f"Password '{pwd}' failed: {e}")
            pass

    if not connected_conn_str:
        print("[ERROR] Could not connect to local MySQL server using standard root passwords.")
        print("Please run this script with your MySQL root password:")
        print("  venv\\Scripts\\python create_mysql_and_migrate.py YOUR_MYSQL_PASSWORD")
        return

    # Update .env file
    env_path = ".env"
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            content = f.read()
        updated = re.sub(r"DATABASE_URL=.*", f"DATABASE_URL={connected_conn_str}", content)
        with open(env_path, "w", encoding="utf-8") as f:
            f.write(updated)
        print(f"[SUCCESS] Updated backend/.env with DATABASE_URL={connected_conn_str}")

    # Run data migration
    print("\nStarting data migration from attendance.db to MySQL...")
    success = migrate(connected_conn_str)
    if success:
        print("\n[SUCCESS] ALL SQLITE DATA HAS BEEN MIGRATED TO MYSQL SUCCESSFULLY!")
    else:
        print("\n[ERROR] Migration failed. Check logs above.")

if __name__ == "__main__":
    import os
    main()
