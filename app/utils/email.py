import asyncio
import logging
import os
import smtplib
import ssl
from email.message import EmailMessage
from urllib.parse import urlencode

logger = logging.getLogger(__name__)


def _send_verification_email_sync(email: str, token: str) -> None:
    frontend_url = os.getenv("FRONTEND_BASE_URL", "http://localhost:5173").rstrip("/")
    query = urlencode({"verification_token": token})
    verification_url = f"{frontend_url}/auth?{query}"
    app_environment = os.getenv("APP_ENV", "development").lower()
    delivery_mode = os.getenv(
        "EMAIL_DELIVERY_MODE",
        "smtp" if app_environment == "production" else "console",
    ).lower()
    print(f"Email verification link for {email}: {verification_url}")
    print(f"Email delivery mode: {delivery_mode}")
    print(f"App environment: {app_environment}")
    print(f"SMTP host: {os.getenv('SMTP_HOST')}")
    print(f"SMTP port: {os.getenv('SMTP_PORT')}")
    print(f"SMTP username: {os.getenv('SMTP_USERNAME')}")
    print(f"SMTP password: {os.getenv('SMTP_PASSWORD')}")
    print(f"SMTP from email: {os.getenv('SMTP_FROM_EMAIL')}")
    if delivery_mode == "console":
        if app_environment == "production":
            raise RuntimeError("Console email delivery is not allowed in production.")
        logger.warning("Email verification link for %s: %s", email, verification_url)
        return
 
    if delivery_mode != "smtp":
        raise RuntimeError("EMAIL_DELIVERY_MODE must be 'console' or 'smtp'.")

    host = os.getenv("SMTP_HOST")
    sender = os.getenv("SMTP_FROM_EMAIL")
    if not host or not sender:
        raise RuntimeError("SMTP_HOST and SMTP_FROM_EMAIL are required for SMTP delivery.")

    message = EmailMessage()
    message["Subject"] = "Verify your Memosphere email"
    message["From"] = sender
    message["To"] = email
    expiration_hours = int(os.getenv("EMAIL_VERIFICATION_EXPIRE_HOURS", "24"))
    message.set_content(
        "Verify your Memosphere email address by opening this link:\n\n"
        f"{verification_url}\n\n"
        f"This link expires after {expiration_hours} hours. "
        "If you did not create this account, ignore this email."
    )

    port = int(os.getenv("SMTP_PORT", "587"))
    username = os.getenv("SMTP_USERNAME")
    password = os.getenv("SMTP_PASSWORD")
    print(f"Connecting to SMTP server {host}:{port} with username {username}")
    with smtplib.SMTP(host, port, timeout=15) as server:
        server.starttls(context=ssl.create_default_context())
        if username and password:
            print(f"Logging in to SMTP server with username {username}")
            server.login(username, password)
        server.send_message(message)


async def send_verification_email(email: str, token: str) -> None:
    await asyncio.to_thread(_send_verification_email_sync, email, token)