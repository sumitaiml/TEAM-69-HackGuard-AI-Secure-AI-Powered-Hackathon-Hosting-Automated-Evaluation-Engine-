from datetime import datetime, timedelta

from app import models


def test_register_sets_verification_token_and_defaults_unverified(client):
    res = client.post("/api/auth/register", json={
        "email": "verify_me@hackeval.ai",
        "password": "password123",
        "full_name": "Verify Me",
        "role": "participant",
    })
    assert res.status_code == 201
    assert res.json()["user"]["is_verified"] is False


def test_verify_email_with_valid_token(client, db_session):
    client.post("/api/auth/register", json={
        "email": "verify2@hackeval.ai",
        "password": "password123",
        "full_name": "Verify Two",
        "role": "participant",
    })
    user = db_session.query(models.User).filter(models.User.email == "verify2@hackeval.ai").first()
    token = user.verification_token
    assert token is not None

    res = client.get(f"/api/auth/verify/{token}")
    assert res.status_code == 200

    db_session.refresh(user)
    assert user.is_verified is True
    assert user.verification_token is None


def test_verify_email_rejects_unknown_token(client):
    res = client.get("/api/auth/verify/not-a-real-token")
    assert res.status_code == 404


def test_forgot_password_does_not_leak_whether_email_exists(client):
    known = client.post("/api/auth/forgot-password", json={"email": "doesnotexist@hackeval.ai"})
    assert known.status_code == 200
    assert "dev_reset_link" not in known.json()  # no account - no link exposed


def test_forgot_password_issues_reset_link_for_real_account(client):
    client.post("/api/auth/register", json={
        "email": "forgot1@hackeval.ai",
        "password": "password123",
        "full_name": "Forgot One",
        "role": "participant",
    })

    res = client.post("/api/auth/forgot-password", json={"email": "forgot1@hackeval.ai"})
    assert res.status_code == 200
    dev_link = res.json().get("dev_reset_link")
    # Must be a bare, usable URL - not the full email body text (a real bug
    # caught here: _send_simple_email originally returned the formatted
    # email body instead of the link itself when SMTP wasn't configured).
    assert dev_link is not None
    assert dev_link.startswith("http")
    assert "reset-password?token=" in dev_link
    assert "\n" not in dev_link


def test_reset_password_with_valid_token_changes_password(client, db_session):
    client.post("/api/auth/register", json={
        "email": "reset1@hackeval.ai",
        "password": "oldpassword123",
        "full_name": "Reset One",
        "role": "participant",
    })
    client.post("/api/auth/forgot-password", json={"email": "reset1@hackeval.ai"})
    user = db_session.query(models.User).filter(models.User.email == "reset1@hackeval.ai").first()
    reset_token = db_session.query(models.PasswordResetToken).filter(
        models.PasswordResetToken.user_id == user.id
    ).first()

    res = client.post(f"/api/auth/reset-password/{reset_token.token}", json={"new_password": "newpassword456"})
    assert res.status_code == 200

    # Old password no longer works, new one does
    old_login = client.post("/api/auth/login", data={"username": "reset1@hackeval.ai", "password": "oldpassword123"})
    assert old_login.status_code == 401
    new_login = client.post("/api/auth/login", data={"username": "reset1@hackeval.ai", "password": "newpassword456"})
    assert new_login.status_code == 200


def test_reset_password_token_cannot_be_reused(client, db_session):
    client.post("/api/auth/register", json={
        "email": "reset2@hackeval.ai",
        "password": "password123",
        "full_name": "Reset Two",
        "role": "participant",
    })
    client.post("/api/auth/forgot-password", json={"email": "reset2@hackeval.ai"})
    user = db_session.query(models.User).filter(models.User.email == "reset2@hackeval.ai").first()
    reset_token = db_session.query(models.PasswordResetToken).filter(
        models.PasswordResetToken.user_id == user.id
    ).first()

    first = client.post(f"/api/auth/reset-password/{reset_token.token}", json={"new_password": "newpassword456"})
    assert first.status_code == 200

    second = client.post(f"/api/auth/reset-password/{reset_token.token}", json={"new_password": "anotherpassword789"})
    assert second.status_code == 400


def test_reset_password_rejects_expired_token(client, db_session):
    client.post("/api/auth/register", json={
        "email": "reset3@hackeval.ai",
        "password": "password123",
        "full_name": "Reset Three",
        "role": "participant",
    })
    client.post("/api/auth/forgot-password", json={"email": "reset3@hackeval.ai"})
    user = db_session.query(models.User).filter(models.User.email == "reset3@hackeval.ai").first()
    reset_token = db_session.query(models.PasswordResetToken).filter(
        models.PasswordResetToken.user_id == user.id
    ).first()
    reset_token.expires_at = datetime.utcnow() - timedelta(hours=1)
    db_session.commit()

    res = client.post(f"/api/auth/reset-password/{reset_token.token}", json={"new_password": "newpassword456"})
    assert res.status_code == 400


def test_reset_password_rejects_unknown_token(client):
    res = client.post("/api/auth/reset-password/not-a-real-token", json={"new_password": "newpassword456"})
    assert res.status_code == 404
