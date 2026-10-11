-- Migration: Create n8n_notification_log table for de-duplication
-- Run this against your attendlens_db MySQL database.

CREATE TABLE IF NOT EXISTS n8n_notification_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    subject_id INT NOT NULL,
    date DATE NOT NULL,
    period INT NOT NULL,
    notified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_n8n_notif_student FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    CONSTRAINT fk_n8n_notif_subject FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
    UNIQUE KEY uq_n8n_notif (student_id, subject_id, date, period),
    INDEX ix_n8n_notif_lookup (subject_id, date, period)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
