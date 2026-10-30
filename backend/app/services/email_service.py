import json
import logging
import smtplib
import urllib.error
import urllib.request
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


def _send_via_resend(to_email: str, subject: str, text_body: str, html_body: Optional[str] = None) -> bool:
    """Sends an email via Resend's REST API over HTTPS port 443.
    This bypasses cloud hosting port blocks (e.g. Render Free tier blocking outbound
    ports 25, 465, and 587). Returns True on success, False on failure."""
    if not settings.RESEND_API_KEY:
        return False

    from_address = f"{settings.SMTP_FROM_NAME} <{settings.RESEND_FROM_EMAIL}>" if settings.SMTP_FROM_NAME else settings.RESEND_FROM_EMAIL

    payload = {
        "from": from_address,
        "to": [to_email],
        "subject": subject,
        "text": text_body,
    }
    if html_body:
        payload["html"] = html_body

    req_data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=req_data,
        headers={
            "Authorization": f"Bearer {settings.RESEND_API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "resend-python/2.0.0",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=settings.SMTP_TIMEOUT_SECONDS) as resp:
            if resp.status in (200, 201):
                logger.info("Email to %s successfully delivered via Resend HTTPS API", to_email)
                return True
            logger.warning("Resend API returned non-success HTTP status %d for %s", resp.status, to_email)
            return False
    except urllib.error.HTTPError as e:
        error_body = ""
        try:
            error_body = e.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        logger.error("Resend API HTTP %d error for %s: %s", e.code, to_email, error_body)
        return False
    except Exception as e:
        logger.error("Resend API request exception for %s (%s): %s", to_email, type(e).__name__, e)
        return False


def send_judge_invite_email(to_email: str, invite_link: str, hackathon_title: str) -> Optional[str]:
    """Sends a real email via Resend HTTP API (port 443) or SMTP (port 587/465).
    If no provider is configured or sending fails, logs the invite link and returns
    it so the caller can surface it directly in the API response (dev_invite_link)."""
    subject = f"You've been invited to judge {hackathon_title}"
    text_content = (
        f"You've been invited to judge \"{hackathon_title}\" on HackGuard / HackEval.\n\n"
        f"Accept your invitation here: {invite_link}\n\n"
        f"This link expires in {settings.JUDGE_INVITE_EXPIRY_DAYS} days."
    )
    html_content = (
        f"<div style='font-family: -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif; max-width: 580px; margin: 0 auto; padding: 24px; border: 1px solid #E2E8F0; border-radius: 16px;'>"
        f"<h2 style='color: #0F172A; margin: 0 0 12px 0;'>Hackathon Judge Invitation</h2>"
        f"<p style='color: #334155; font-size: 15px; line-height: 1.6; margin: 0 0 20px 0;'>You have been invited to judge <strong>{hackathon_title}</strong> on HackGuard.</p>"
        f"<div style='margin: 24px 0;'>"
        f"<a href='{invite_link}' style='display: inline-block; background: #2563EB; color: #FFFFFF; font-weight: 700; text-decoration: none; padding: 12px 28px; border-radius: 99px; font-size: 14px;'>Accept Judge Invitation</a>"
        f"</div>"
        f"<p style='color: #64748B; font-size: 13px; margin: 0 0 8px 0;'>Or open this link directly in your browser:</p>"
        f"<p style='word-break: break-all; margin: 0 0 20px 0;'><a href='{invite_link}' style='color: #2563EB;'>{invite_link}</a></p>"
        f"<p style='color: #94A3B8; font-size: 12px; margin: 0;'>This invitation expires in {settings.JUDGE_INVITE_EXPIRY_DAYS} days.</p>"
        f"</div>"
    )

    # 1. Primary: Resend HTTPS API (port 443 - unblocked on Render Free tier and all cloud hosts)
    if settings.RESEND_API_KEY:
        if _send_via_resend(to_email, subject, text_content, html_content):
            return None
        logger.warning("Resend delivery failed for %s, falling back to SMTP/direct link", to_email)

    # 2. Secondary: SMTP (local docker, or cloud instances with unblocked SMTP ports)
    if settings.SMTP_HOST:
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = _from_header()
        message["To"] = to_email
        message.set_content(text_content)
        message.add_alternative(html_content, subtype="html")

        try:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=settings.SMTP_TIMEOUT_SECONDS) as server:
                if settings.SMTP_USE_TLS:
                    server.starttls()
                if settings.SMTP_USERNAME:
                    server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                server.send_message(message)
            return None
        except (smtplib.SMTPException, OSError) as e:
            logger.error("SMTP send failed for %s (%s: %s), falling back to direct link: %s", to_email, type(e).__name__, e, invite_link)
            return invite_link

    logger.info("No active email provider configured - judge invite link for %s: %s", to_email, invite_link)
    return invite_link


def _send_simple_email(to_email: str, subject: str, body: str, link: str) -> Optional[str]:
    """Shared send path for password reset and email verification."""
    # 1. Primary: Resend HTTPS API (port 443)
    if settings.RESEND_API_KEY:
        if _send_via_resend(to_email, subject, body):
            return None
        logger.warning("Resend delivery failed for %s, falling back to SMTP/direct link", to_email)

    # 2. Secondary: SMTP
    if settings.SMTP_HOST:
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = _from_header()
        message["To"] = to_email
        message.set_content(body)

        try:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=settings.SMTP_TIMEOUT_SECONDS) as server:
                if settings.SMTP_USE_TLS:
                    server.starttls()
                if settings.SMTP_USERNAME:
                    server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                server.send_message(message)
            return None
        except (smtplib.SMTPException, OSError) as e:
            logger.error("SMTP send failed for %s (%s: %s), falling back to direct link: %s", to_email, type(e).__name__, e, link)
            return link

    logger.info("No active email provider configured - link for %s: %s", to_email, link)
    return link


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
