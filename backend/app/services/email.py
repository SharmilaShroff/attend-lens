import smtplib
import re
from typing import Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import get_settings

settings = get_settings()


def validate_email(email_str: str) -> bool:
    """Validates basic email format."""
    if not email_str or not isinstance(email_str, str):
        return False
    email_str = email_str.strip()
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return bool(re.match(pattern, email_str))


def send_email(to_email: str, subject: str, body: str, html_body: Optional[str] = None) -> bool:
    """
    Sends an email using Gmail SMTP or standard SMTP.
    If EMAIL_DRY_RUN=True or credentials are not configured, it safely logs the email instead.
    """
    if not validate_email(to_email):
        print(f"[EMAIL SKIP] Invalid email address format: '{to_email}'")
        return False

    gmail_user = getattr(settings, "GMAIL_USER", "").strip()
    gmail_pass = getattr(settings, "GMAIL_APP_PASSWORD", "").replace(" ", "").strip()
    from_name = getattr(settings, "EMAIL_FROM_NAME", "Attend Lens")

    smtp_host = settings.SMTP_HOST
    smtp_port = settings.SMTP_PORT or 587
    smtp_user = settings.SMTP_USER
    smtp_pass = (settings.SMTP_PASS or settings.SMTP_PASSWORD or "").strip()
    from_address = settings.EMAIL_FROM or settings.SMTP_FROM or "attendance@attendlens.edu"

    is_gmail = bool(gmail_user and gmail_pass)
    has_smtp = bool(smtp_host and smtp_user)

    # Dry-run mode or unconfigured credentials -> log email safely
    if settings.EMAIL_DRY_RUN or (not is_gmail and not has_smtp):
        sender_display = f"{from_name} <{gmail_user}>" if is_gmail else from_address
        print(f"\n==================== [EMAIL DRY RUN LOG] ====================")
        print(f"From: {sender_display}")
        print(f"To: {to_email}")
        print(f"Subject: {subject}")
        print(f"--- PLAIN TEXT ---\n{body}")
        print(f"=============================================================\n")
        return True

    try:
        msg = MIMEMultipart("alternative")
        if is_gmail:
            msg["From"] = f"{from_name} <{gmail_user}>"
            sender_email = gmail_user
            auth_user = gmail_user
            auth_pass = gmail_pass
        else:
            msg["From"] = from_address
            sender_email = from_address
            auth_user = smtp_user
            auth_pass = smtp_pass

        msg["To"] = to_email
        msg["Subject"] = subject

        msg.attach(MIMEText(body, "plain", "utf-8"))
        if html_body:
            msg.attach(MIMEText(html_body, "html", "utf-8"))

        server_sent = False
        last_exception = None

        # Try Gmail STARTTLS port 587 first, then SSL port 465 if configured
        ports_to_try = [587, 465] if is_gmail else [smtp_port]

        for p in ports_to_try:
            try:
                if p == 465:
                    server = smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=12)
                    server.ehlo()
                else:
                    target_host = "smtp.gmail.com" if is_gmail else smtp_host
                    server = smtplib.SMTP(target_host, p, timeout=12)
                    server.ehlo()
                    server.starttls()
                    server.ehlo()

                server.login(auth_user, auth_pass)
                server.sendmail(sender_email, to_email, msg.as_string())
                server.quit()
                server_sent = True
                print(f"[EMAIL SENT] Successfully sent email to {to_email} via port {p}")
                break
            except Exception as ex:
                last_exception = ex

        if not server_sent:
            err_str = str(last_exception)
            if "535" in err_str or "BadCredentials" in err_str:
                print(f"[EMAIL ERROR] Gmail rejected credentials for {gmail_user} (535 BadCredentials). Please generate a fresh 16-char App Password at https://myaccount.google.com/apppasswords")
            else:
                print(f"[EMAIL WARN] SMTP send attempt failed ({last_exception}). Falling back to safe logging.")
            print(f"To: {to_email} | Subject: {subject}\n--- BODY ---\n{body[:200]}...\n")
            return False

        return True
    except Exception as e:
        print(f"[EMAIL ERROR] Failed to process email to {to_email}: {e}")
        return False


