import logging
import smtplib
from email.message import EmailMessage
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)


def send_judge_invite_email(to_email: str, invite_link: str, hackathon_title: str) -> Optional[str]:
    """Sends a real email if SMTP_HOST is configured. Otherwise logs the
    invite link and returns it so the caller can surface it directly in the
    API response (dev_invite_link) - the feature works end-to-end without a
    real mail provider, and wiring one in later is a config change only."""
    if not settings.SMTP_HOST:
        logger.info("SMTP not configured - judge invite link for %s: %s", to_email, invite_link)
        return invite_link

    message = EmailMessage()
    message["Subject"] = f"You've been invited to judge {hackathon_title}"
    message["From"] = settings.SMTP_FROM_ADDRESS
    message["To"] = to_email
    message.set_content(
        f"You've been invited to judge \"{hackathon_title}\" on HackGuard AI.\n\n"
        f"Accept your invitation here: {invite_link}\n\n"
        f"This link expires in {settings.JUDGE_INVITE_EXPIRY_DAYS} days."
    )

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        if settings.SMTP_USE_TLS:
            server.starttls()
        if settings.SMTP_USERNAME:
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        server.send_message(message)

    return None
