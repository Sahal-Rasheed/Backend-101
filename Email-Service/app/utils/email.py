import resend
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.core.config import settings

resend.api_key = settings.RESEND_API_KEY


def send_email_via_smtp(to_email: str, subject: str, html_content: str) -> dict:
    """
    Fallback email sending via SMTP if Resend API fails.
    """
    msg = MIMEMultipart()
    msg["From"] = settings.SMTP_USER
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(html_content, "html"))
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASS)
        server.send_message(msg)

    return {"provider": "smtp", "provider_id": None, "status": "sent"}


def send_email_via_resend(to_email: str, subject: str, html_content: str) -> dict:
    """
    Primary email sending via Resend API.
    """
    params: resend.Emails.SendParams = {
        "from": settings.RESEND_SENDER_EMAIL,
        "to": [to_email],
        "subject": subject,
        "html": html_content,
    }
    email_resp = resend.Emails.send(params)
    return {"provider": "resend", "provider_id": email_resp.id, "status": "sent"}


def send_email(to_email: str, subject: str, html_content: str) -> dict:
    """
    Unified email sending handler.
    Tries Resend API first, then falls back to SMTP if it fails.
    """
    try:
        return send_email_via_resend(to_email, subject, html_content)
    except Exception as ex:
        print(f"Error sending email via Resend: {ex}")
        print("Falling back to SMTP email sending!")
        try:
            return send_email_via_smtp(to_email, subject, html_content)
        except Exception as smtp_ex:
            print(f"Error sending email (fallback) via SMTP: {smtp_ex}")
            raise Exception("Both Resend and SMTP email sending failed")
