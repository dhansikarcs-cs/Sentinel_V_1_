import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger("sentinel.notification")


def send_email(to: str, subject: str, body: str) -> bool:
    logger.info("Sending email to %s: %s", to, subject)
    if not settings.smtp_host:
        logger.warning("SMTP not configured — email logged only")
        return False
    try:
        msg = EmailMessage()
        msg.set_content(body)
        msg["Subject"] = subject
        msg["From"] = settings.email_from
        msg["To"] = to
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as s:
            s.ehlo()
            s.starttls()
            s.ehlo()
            s.login(settings.smtp_user, settings.smtp_password)
            s.send_message(msg)
        logger.info("Email sent successfully to %s", to)
        return True
    except smtplib.SMTPAuthenticationError:
        logger.error(
            "SMTP auth failed — app password may be expired. Generate new one at https://myaccount.google.com/apppasswords"
        )
        return False
    except Exception as e:
        logger.error("Email send failed: %s: %s", type(e).__name__, e)
        return False
