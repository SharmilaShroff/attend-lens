import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import get_settings

settings = get_settings()


def send_email(to_email: str, subject: str, body: str) -> bool:
    """
    Sends an email using standard SMTP.
    If SMTP_HOST or SMTP_USER is not configured in .env, it safely logs the email instead.
    """
    if not settings.SMTP_HOST or not settings.SMTP_USER:
        print(f"[EMAIL MOCK LOG] To: {to_email} | Subject: {subject}\nBody: {body}\n")
        return True

    try:
        msg = MIMEMultipart()
        msg['From'] = settings.SMTP_FROM
        msg['To'] = to_email
        msg['Subject'] = subject

        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
        server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.sendmail(settings.SMTP_FROM, to_email, msg.as_string())
        server.quit()
        print(f"[EMAIL SENT] Successfully sent email to {to_email}")
        return True
    except Exception as e:
        print(f"[EMAIL ERROR] Failed to send email to {to_email}: {e}")
        return False
