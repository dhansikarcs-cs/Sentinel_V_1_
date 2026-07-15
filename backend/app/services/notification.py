import smtplib
from email.message import EmailMessage

from app.core.config import settings


def send_email(subject: str, body: str, to: str = "") -> bool:
    if not settings.smtp_host or not settings.smtp_user:
        return False
    try:
        msg = EmailMessage()
        msg.set_content(body)
        msg["Subject"] = subject
        msg["From"] = settings.email_from
        msg["To"] = to or settings.smtp_user
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.starttls()
            server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)
        return True
    except Exception:
        return False
