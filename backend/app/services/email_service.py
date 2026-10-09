import logging
import smtplib
from email.message import EmailMessage
from email.utils import formataddr
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)


def _from_header() -> str:
    """Builds a proper 'Display Name <address>' From header (formataddr
    handles quoting/escaping correctly, unlike raw string interpolation).
    Note: most providers (Gmail included) still enforce that the address
    itself matches the authenticated account, rewriting it if it doesn't -
    but the display name portion passes through either way."""
    if settings.SMTP_FROM_NAME:
        return formataddr((settings.SMTP_FROM_NAME, settings.SMTP_FROM_ADDRESS))
    return settings.SMTP_FROM_ADDRESS


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
    message["From"] = _from_header()
    message["To"] = to_email
    message.set_content(
        f"You've been invited to judge \"{hackathon_title}\" on HackEval.\n\n"
        f"Accept your invitation here: {invite_link}\n\n"
        f"This link expires in {settings.JUDGE_INVITE_EXPIRY_DAYS} days."
    )

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            if settings.SMTP_USE_TLS:
                server.starttls()
            if settings.SMTP_USERNAME:
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(message)
    except (smtplib.SMTPException, OSError) as e:
        # A bad password, an unreachable host, a provider outage - none of
        # these should take down judge invites entirely. Degrade the same
        # way as "SMTP not configured": log it and hand the link back
        # directly so the feature still works end-to-end.
        logger.error("SMTP send failed for %s, falling back to direct link: %s", to_email, e)
        return invite_link

    return None


def _send_simple_email(to_email: str, subject: str, body: str, link: str) -> Optional[str]:
    """Shared send-or-log-link path used by both password reset and email
    verification - same dev-fallback behavior as send_judge_invite_email,
    factored out since neither needs the invite-specific fields. Returns
    just the bare `link` (not the full email body) when unsent, matching
    send_judge_invite_email's contract - the caller surfaces this as
    dev_reset_link/dev_verify_link, which should be a usable URL, not prose."""
    if not settings.SMTP_HOST:
        logger.info("SMTP not configured - link for %s: %s", to_email, link)
        return link

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = _from_header()
    message["To"] = to_email
    message.set_content(body)

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            if settings.SMTP_USE_TLS:
                server.starttls()
            if settings.SMTP_USERNAME:
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(message)
    except (smtplib.SMTPException, OSError) as e:
        logger.error("SMTP send failed for %s, falling back to direct link: %s", to_email, e)
        return link

    return None


def send_password_reset_email(to_email: str, reset_link: str) -> Optional[str]:
    return _send_simple_email(
        to_email,
        "Reset your HackEval password",
        f"We received a request to reset your password.\n\n"
        f"Reset it here: {reset_link}\n\n"
        f"This link expires in {settings.PASSWORD_RESET_EXPIRY_HOURS} hours. "
        f"If you didn't request this, you can safely ignore this email.",
        link=reset_link,
    )


def send_verification_email(to_email: str, verify_link: str) -> Optional[str]:
    return _send_simple_email(
        to_email,
        "Verify your HackEval email address",
        f"Welcome to HackEval! Please verify your email address:\n\n{verify_link}",
        link=verify_link,
    )
