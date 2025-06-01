from db import SessionLocal, User, UserToken
from calendar_summary import generate_summary_html
from google.oauth2.credentials import Credentials
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta
import os

# === Email configuration ===
FROM_EMAIL = os.getenv("FROM_EMAIL")
APP_PASSWORD = os.getenv("APP_PASSWORD")
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = os.getenv("SMTP_PORT")

# === Utility: Check if summary has events ===
def is_summary_empty(html: str) -> bool:
    return 'class="event"' not in html

# === Send the email ===
def send_email(to_email: str, html_body: str, has_events: bool):
    tomorrow_str = (datetime.now() + timedelta(days=1)).strftime("%A, %B %d, %Y")
    subject = (
        f"📅 {tomorrow_str} — Daily Schedule Summary"
        if has_events else
        f"🎉 {tomorrow_str} — No Events Scheduled"
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = FROM_EMAIL
    msg["To"] = to_email
    msg.attach(MIMEText(html_body, "html", _charset="utf-8"))

    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(FROM_EMAIL, APP_PASSWORD)
            server.sendmail(FROM_EMAIL, to_email, msg.as_string())
        print(f"✅ Email sent to {to_email}")
    except Exception as e:
        print(f"❌ Failed to send to {to_email}: {e}")

# === Main execution ===
db = SessionLocal()
users = db.query(User).all()

for user in users:
    try:
        tokens = db.query(UserToken).filter_by(user_id=user.id).all()
        user_credentials = {
            token.google_email: Credentials.from_authorized_user_file(token.token_path)
            for token in tokens
        }

        print(f"🧩 {user.email} linked calendars: {list(user_credentials.keys())}")

        if not user_credentials:
            print(f"⚠️ No credentials found for {user.email}")
            continue

        summary_html = generate_summary_html(user_credentials)
        empty = is_summary_empty(summary_html)

        if empty:
            summary_html = f"""
            <html>
            <body style="font-family: 'Segoe UI', sans-serif; padding: 20px; background: #f9f9ff; color: #333;">
                <h1 style="color: #5b4fc7;">🎉 Yay, it’s a free day!</h1>
                <p>No meetings, no stress — just you and the things you love. 💜</p>
            </body>
            </html>
            """

        send_email(user.email, summary_html, has_events=not empty)

    except Exception as e:
        print(f"❌ Error processing {user.email}: {e}")

db.close()
