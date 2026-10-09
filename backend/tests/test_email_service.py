import smtplib

import pytest

import app.services.email_service as email_service_module
from app.services.email_service import _from_header, send_judge_invite_email, send_password_reset_email


class _FakeSMTPSuccess:
    sent_messages = []

    def __init__(self, *a, **k):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def starttls(self):
        pass

    def login(self, *a, **k):
        pass

    def send_message(self, message, *a, **k):
        _FakeSMTPSuccess.sent_messages.append(message)


class _FakeSMTPAuthFailure:
    def __init__(self, *a, **k):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def starttls(self):
        pass

    def login(self, *a, **k):
        raise smtplib.SMTPAuthenticationError(535, b"Authentication failed")

    def send_message(self, *a, **k):
        pass


@pytest.fixture
def smtp_configured(monkeypatch):
    monkeypatch.setattr(email_service_module.settings, "SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr(email_service_module.settings, "SMTP_USERNAME", "user@example.com")
    monkeypatch.setattr(email_service_module.settings, "SMTP_PASSWORD", "whatever")


def test_judge_invite_email_sends_successfully(smtp_configured, monkeypatch):
    monkeypatch.setattr(smtplib, "SMTP", _FakeSMTPSuccess)
    result = send_judge_invite_email("judge@example.com", "http://localhost/accept?token=abc", "Test Hack")
    assert result is None  # None = genuinely sent, no fallback link needed


def test_judge_invite_email_falls_back_on_auth_failure(smtp_configured, monkeypatch):
    """The real bug this covers: a bad password (or any SMTP failure) used
    to raise all the way up to a 500 instead of degrading gracefully, same
    as the project's existing pattern for a Gemini/Docker outage."""
    monkeypatch.setattr(smtplib, "SMTP", _FakeSMTPAuthFailure)
    link = "http://localhost/accept-invite?token=abc"
    result = send_judge_invite_email("judge@example.com", link, "Test Hack")
    assert result == link


def test_password_reset_email_falls_back_on_connection_failure(smtp_configured, monkeypatch):
    class _FakeSMTPConnectionFailure:
        def __init__(self, *a, **k):
            raise OSError("Connection refused")

    monkeypatch.setattr(smtplib, "SMTP", _FakeSMTPConnectionFailure)
    link = "http://localhost/reset-password?token=xyz"
    result = send_password_reset_email("user@example.com", link)
    assert result == link


def test_password_reset_email_sends_successfully(smtp_configured, monkeypatch):
    monkeypatch.setattr(smtplib, "SMTP", _FakeSMTPSuccess)
    result = send_password_reset_email("user@example.com", "http://localhost/reset-password?token=xyz")
    assert result is None


def test_from_header_includes_display_name_when_configured(monkeypatch):
    monkeypatch.setattr(email_service_module.settings, "SMTP_FROM_NAME", "HackGuard AI")
    monkeypatch.setattr(email_service_module.settings, "SMTP_FROM_ADDRESS", "no-reply@hackguard.ai")
    assert _from_header() == "HackGuard AI <no-reply@hackguard.ai>"


def test_from_header_falls_back_to_bare_address_without_a_name(monkeypatch):
    monkeypatch.setattr(email_service_module.settings, "SMTP_FROM_NAME", "")
    monkeypatch.setattr(email_service_module.settings, "SMTP_FROM_ADDRESS", "no-reply@hackguard.ai")
    assert _from_header() == "no-reply@hackguard.ai"


def test_sent_email_actually_carries_the_display_name(smtp_configured, monkeypatch):
    monkeypatch.setattr(email_service_module.settings, "SMTP_FROM_NAME", "HackGuard AI")
    monkeypatch.setattr(email_service_module.settings, "SMTP_FROM_ADDRESS", "no-reply@hackguard.ai")
    _FakeSMTPSuccess.sent_messages = []
    monkeypatch.setattr(smtplib, "SMTP", _FakeSMTPSuccess)

    send_password_reset_email("user@example.com", "http://localhost/reset-password?token=xyz")

    assert len(_FakeSMTPSuccess.sent_messages) == 1
    assert _FakeSMTPSuccess.sent_messages[0]["From"] == "HackGuard AI <no-reply@hackguard.ai>"
