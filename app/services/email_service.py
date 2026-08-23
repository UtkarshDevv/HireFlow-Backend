"""
Email Notification Service adhering to Object-Oriented Programming (OOPS) Principles.
Dispatches new user signup alerts to the platform administrator.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
import smtplib
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import logging
from typing import Optional

from app.config import get_settings

logger = logging.getLogger(__name__)


class BaseEmailNotifier(ABC):
    """
    Abstract Base Class for email notification services.
    Demonstrates Abstraction and defines the notification interface contract.
    """

    @abstractmethod
    def send_signup_notification(self, name: str, email: str, metadata: Optional[dict] = None) -> bool:
        """Send a new user signup notification email."""
        pass


class SMTPEmailNotifier(BaseEmailNotifier):
    """
    Concrete Email Notifier using SMTP protocol.
    Demonstrates Encapsulation of SMTP transport, template generation, and async dispatching.
    """

    def __init__(
        self,
        admin_email: str = "utkarshsinha2122@gmail.com",
        smtp_host: Optional[str] = None,
        smtp_port: int = 587,
        smtp_user: Optional[str] = None,
        smtp_password: Optional[str] = None,
        from_email: Optional[str] = None,
        from_name: str = "HireFlow Platform",
    ):
        self._admin_email = admin_email
        self._smtp_host = smtp_host or ""
        self._smtp_port = smtp_port
        self._smtp_user = smtp_user or ""
        self._smtp_password = smtp_password or ""
        self._from_email = from_email or self._smtp_user or "notifications@hireflow.app"
        self._from_name = from_name

    def _build_html_content(self, name: str, email: str, signup_time: str) -> str:
        """Encapsulated method generating responsive, premium HTML email body."""
        return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 24px; color: #1e293b; }}
    .container {{ max-width: 580px; margin: 0 auto; background: #ffffff; border-radius: 16px; border: 1px solid #e2e8f0; overflow: hidden; box-shadow: 0 10px 25px rgba(0,0,0,0.05); }}
    .header {{ background: linear-gradient(135deg, #1d63ff 0%, #00d2b4 100%); padding: 32px 28px; text-align: center; color: #ffffff; }}
    .header h1 {{ margin: 0; font-size: 24px; font-weight: 800; letter-spacing: -0.02em; }}
    .header p {{ margin: 6px 0 0; opacity: 0.9; font-size: 14px; }}
    .content {{ padding: 28px; }}
    .user-card {{ background: #f1f5f9; border-radius: 12px; padding: 20px; margin: 20px 0; border: 1px solid #e2e8f0; }}
    .field-row {{ display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #e2e8f0; font-size: 14px; }}
    .field-row:last-child {{ border-bottom: none; }}
    .field-label {{ color: #64748b; font-weight: 600; }}
    .field-value {{ color: #0f172a; font-weight: 700; }}
    .footer {{ padding: 18px 28px; background: #f8fafc; border-top: 1px solid #e2e8f0; text-align: center; font-size: 12px; color: #94a3b8; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>🎉 New User Registered!</h1>
      <p>A new candidate has joined the HireFlow AI Career Platform</p>
    </div>
    <div class="content">
      <p style="font-size: 15px; line-height: 1.6; margin-top: 0;">
        Hello Utkarsh, a new user has successfully registered their account on <strong>HireFlow</strong>:
      </p>
      <div class="user-card">
        <div class="field-row">
          <span class="field-label">Candidate Name:</span>
          <span class="field-value">{name}</span>
        </div>
        <div class="field-row">
          <span class="field-label">Email Address:</span>
          <span class="field-value" style="color: #1d63ff;">{email}</span>
        </div>
        <div class="field-row">
          <span class="field-label">Registration Time:</span>
          <span class="field-value">{signup_time} UTC</span>
        </div>
        <div class="field-row">
          <span class="field-label">Status:</span>
          <span class="field-value" style="color: #10b981;">Active / Verified</span>
        </div>
      </div>
      <p style="font-size: 13px; color: #64748b; line-height: 1.5;">
        Their personalized course roadmap and career dashboard have been automatically initialized.
      </p>
    </div>
    <div class="footer">
      Sent automatically by HireFlow AI Career Platform Backend Notification Service.
    </div>
  </div>
</body>
</html>"""

    def _send_sync(self, name: str, email: str, signup_time: str) -> bool:
        """Internal synchronous transmission worker."""
        # Dynamically load latest settings to support live .env changes
        settings = get_settings()
        admin_email = settings.admin_notification_email or self._admin_email or "utkarshsinha2122@gmail.com"
        smtp_host = settings.smtp_host or self._smtp_host
        smtp_port = settings.smtp_port or self._smtp_port or 587
        smtp_user = settings.smtp_user or self._smtp_user
        smtp_password = settings.smtp_password or self._smtp_password
        from_email = settings.smtp_from_email or self._from_email or smtp_user or "notifications@hireflow.app"
        from_name = settings.smtp_from_name or self._from_name

        subject = f"New HireFlow User Signup: {name} ({email})"
        html_body = self._build_html_content(name, email, signup_time)

        # Print visible terminal alert
        print("\n" + "=" * 60)
        print(f"[ADMIN SIGNUP NOTIFICATION]")
        print(f"To: {admin_email}")
        print(f"Subject: {subject}")
        print(f"User: {name} <{email}>")
        print(f"Time: {signup_time} UTC")
        print("=" * 60 + "\n")

        if not smtp_host or not smtp_user or not smtp_password:
            print("[INFO] SMTP password is not set in backend/.env yet.")
            print(f"   To receive emails directly in {admin_email}:")
            print("   1. Open backend/.env")
            print("   2. Set SMTP_PASSWORD=<your-16-char-gmail-app-password>")
            print("   3. Generate password at: https://myaccount.google.com/apppasswords")
            return True

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{from_name} <{from_email}>"
            msg["To"] = admin_email

            part_text = MIMEText(
                f"New HireFlow User Signup:\nName: {name}\nEmail: {email}\nTime: {signup_time} UTC",
                "plain",
            )
            part_html = MIMEText(html_body, "html")

            msg.attach(part_text)
            msg.attach(part_html)

            # Support both port 465 (SSL) and port 587 (STARTTLS)
            if smtp_port == 465:
                with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=15) as server:
                    server.login(smtp_user, smtp_password)
                    server.sendmail(from_email, [admin_email], msg.as_string())
            else:
                with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
                    server.ehlo()
                    try:
                        server.starttls()
                        server.ehlo()
                    except Exception:
                        pass
                    server.login(smtp_user, smtp_password)
                    server.sendmail(from_email, [admin_email], msg.as_string())

            logger.info(f"Notification email successfully delivered to {admin_email}")
            print(f"[SUCCESS] Notification email successfully delivered to {admin_email}")
            return True
        except Exception as e:
            logger.warning(f"SMTP delivery failed ({e}). Signup succeeded without blocking.")
            print(f"[ERROR] SMTP delivery error: {e}")
            return False

    def send_signup_notification(self, name: str, email: str, metadata: Optional[dict] = None) -> bool:
        """
        Asynchronously triggers the email notification in a daemon thread.
        Guarantees non-blocking, zero-latency user registration.
        """
        signup_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        thread = threading.Thread(
            target=self._send_sync,
            args=(name, email, signup_time),
            daemon=True,
            name=f"email-signup-{email}",
        )
        thread.start()
        return True


class EmailNotifierFactory:
    """
    Factory Class providing unified instantiation of email notifiers.
    Demonstrates the Factory Design Pattern in OOP.
    """

    @staticmethod
    def create_notifier() -> BaseEmailNotifier:
        settings = get_settings()
        return SMTPEmailNotifier(
            admin_email=settings.admin_notification_email or "utkarshsinha2122@gmail.com",
            smtp_host=settings.smtp_host,
            smtp_port=settings.smtp_port,
            smtp_user=settings.smtp_user,
            smtp_password=settings.smtp_password,
            from_email=settings.smtp_from_email,
            from_name=settings.smtp_from_name,
        )


# Global singleton instance for easy dependency injection
email_notifier: BaseEmailNotifier = EmailNotifierFactory.create_notifier()
