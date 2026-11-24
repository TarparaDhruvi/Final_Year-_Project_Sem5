"""
utils/email.py
Sends transactional email over Gmail SMTP (verification + password reset).
Uses smtplib directly (no extra dependency) with a small HTML template
that carries StudentHub branding.

To use this for real: create a Google Account App Password (Google Account
-> Security -> 2-Step Verification -> App Passwords) and put it in
SMTP_APP_PASSWORD in your .env. Regular Gmail passwords will not work.
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_APP_PASSWORD = os.getenv("SMTP_APP_PASSWORD", "")
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "StudentHub")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")


def email_configured() -> bool:
    """True only when real SMTP credentials are present (placeholders from .env.example don't count)."""
    user, pw = os.getenv("SMTP_USERNAME", SMTP_USERNAME), os.getenv("SMTP_APP_PASSWORD", SMTP_APP_PASSWORD)
    return bool(user and pw) and not user.startswith("youraccount") and not pw.startswith("your-")


def _send(to_email: str, subject: str, html_body: str, log_body: bool = True) -> bool:
    """
    Sends an email. Returns True on success. If SMTP credentials aren't
    configured (e.g. local dev without a Gmail App Password yet), it logs
    the email to the console instead of raising, so the rest of the app
    keeps working.
    """
    if not email_configured():
        print("=" * 60)
        print("SMTP not configured — email NOT sent.")
        print(f"To: {to_email}\nSubject: {subject}" + (f"\n{html_body}" if log_body else "\n(body withheld: contains a secret link)"))
        print("=" * 60)
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{SMTP_FROM_NAME} <{SMTP_USERNAME}>"
    msg["To"] = to_email
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_APP_PASSWORD)
        server.sendmail(SMTP_USERNAME, to_email, msg.as_string())
    return True


def _base_template(title: str, name: str, body_html: str, warning: str) -> str:
    return f"""
    <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 480px; margin: 0 auto;
                background: #F8FAFC; padding: 32px; border-radius: 16px;">
      <div style="text-align:center; margin-bottom:24px;">
        <div style="display:inline-block; background: linear-gradient(135deg, #2563EB, #38BDF8);
                    color:white; font-weight:700; font-size:20px; padding:10px 20px; border-radius:12px;">
          StudentHub
        </div>
      </div>
      <h2 style="color:#0F172A; margin-bottom:8px;">{title}</h2>
      <p style="color:#334155; font-size:15px;">Hi {name},</p>
      {body_html}
      <p style="color:#94A3B8; font-size:12px; margin-top:32px; border-top:1px solid #E2E8F0; padding-top:16px;">
        ⚠️ {warning}
      </p>
    </div>
    """


def send_verification_email(to_email: str, name: str, token: str):
    link = f"{FRONTEND_URL}/verify-email?token={token}"
    body = f"""
      <p style="color:#334155; font-size:15px;">Welcome to StudentHub! Please verify your email to activate your account.</p>
      <div style="text-align:center; margin:24px 0;">
        <a href="{link}" style="background:#2563EB; color:white; padding:12px 28px; border-radius:10px;
           text-decoration:none; font-weight:600;">Verify Email</a>
      </div>
      <p style="color:#64748B; font-size:13px;">This link expires in 24 hours.</p>
    """
    html = _base_template(
        "Verify your email",
        name,
        body,
        "If you didn't create a StudentHub account, you can safely ignore this email.",
    )
    return _send(to_email, "Verify your StudentHub account", html)


def send_password_reset_email(to_email: str, name: str, token: str):
    link = f"{FRONTEND_URL}/reset-password?token={token}"
    body = f"""
      <p style="color:#334155; font-size:15px;">We received a request to reset your StudentHub password.</p>
      <div style="text-align:center; margin:24px 0;">
        <a href="{link}" style="background:#2563EB; color:white; padding:12px 28px; border-radius:10px;
           text-decoration:none; font-weight:600;">Reset Password</a>
      </div>
      <p style="color:#64748B; font-size:13px;">This link expires in 15 minutes and can only be used once.</p>
    """
    html = _base_template(
        "Reset your password",
        name,
        body,
        "If you didn't request this, please ignore this email — your password will remain unchanged.",
    )
    return _send(to_email, "Reset your StudentHub password", html, log_body=False)   # never log reset links


def send_faculty_welcome_email(to_email: str, name: str, faculty_id: str, temp_password: str):
    """
    Sent automatically when an Admin creates a Faculty account. Faculty
    accounts are never self-registered, so this email is the faculty
    member's only way to learn their login credentials.
    """
    link = f"{FRONTEND_URL}/login/faculty"
    body = f"""
      <p style="color:#334155; font-size:15px;">An Admin has created a Faculty account for you on StudentHub.
      Here are your login credentials:</p>
      <div style="background:white; border-radius:12px; padding:16px 20px; margin:20px 0; border:1px solid #E2E8F0;">
        <p style="margin:4px 0; color:#0F172A;"><strong>Faculty ID:</strong> {faculty_id}</p>
        <p style="margin:4px 0; color:#0F172A;"><strong>Email:</strong> {to_email}</p>
        <p style="margin:4px 0; color:#0F172A;"><strong>Temporary Password:</strong> {temp_password}</p>
      </div>
      <div style="text-align:center; margin:24px 0;">
        <a href="{link}" style="background:#2563EB; color:white; padding:12px 28px; border-radius:10px;
           text-decoration:none; font-weight:600;">Log in to Faculty Portal</a>
      </div>
      <p style="color:#64748B; font-size:13px;">Please change this temporary password after your first login.</p>
    """
    html = _base_template(
        "Welcome to StudentHub",
        name,
        body,
        "Keep your Faculty ID and password private — they identify you on the Faculty Portal.",
    )
    return _send(to_email, "Your StudentHub Faculty account", html)
