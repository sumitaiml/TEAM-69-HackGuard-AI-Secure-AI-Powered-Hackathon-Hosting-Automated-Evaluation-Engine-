import io

import pytest

from app import models


def _register(client, email, full_name, role="participant"):
    res = client.post("/api/auth/register", json={
        "email": email, "password": "password123", "full_name": full_name, "role": role
    })
    return res


def _create_org_and_hackathon(client, org_email, title):
    org_res = _register(client, org_email, "Org", role="organizer")
    org_headers = {"Authorization": f"Bearer {org_res.json()['access_token']}"}
    hack_res = client.post("/api/hackathons/create", json={"title": title}, headers=org_headers)
    return org_headers, hack_res.json()["id"]


def test_register_rejects_judge_and_admin_roles(client):
    judge_res = _register(client, "sneaky_judge@hackeval.ai", "Sneaky", role="judge")
    assert judge_res.status_code == 422

    admin_res = _register(client, "sneaky_admin@hackeval.ai", "Sneaky", role="admin")
    assert admin_res.status_code == 422


def test_judge_invite_accept_flow_end_to_end(client, db_session):
    org_headers, hack_id = _create_org_and_hackathon(client, "invite_org@hackeval.ai", "Invite Flow Event")

    invite_res = client.post(
        f"/api/hackathons/{hack_id}/invite-judge",
        json={"email": "new_judge@hackeval.ai"},
        headers=org_headers
    )
    assert invite_res.status_code == 201
    invite_data = invite_res.json()
    assert invite_data["status"] == "pending"
    assert "dev_invite_link" in invite_data  # no SMTP configured in tests
    token = invite_data["dev_invite_link"].split("token=")[1]

    # GET invite details works before acceptance
    details_res = client.get(f"/api/auth/invite/{token}")
    assert details_res.status_code == 200
    assert details_res.json()["email"] == "new_judge@hackeval.ai"
    assert details_res.json()["hackathon_title"] == "Invite Flow Event"

    accept_res = client.post(
        f"/api/auth/invite/{token}/accept",
        json={"full_name": "New Judge", "password": "password123"}
    )
    assert accept_res.status_code == 200
    body = accept_res.json()
    assert body["user"]["role"] == "judge"
    assert body["user"]["email"] == "new_judge@hackeval.ai"
    assert "access_token" in body

    # Re-accepting the same (now-used) token fails
    reaccept_res = client.post(
        f"/api/auth/invite/{token}/accept",
        json={"full_name": "New Judge", "password": "password123"}
    )
    assert reaccept_res.status_code == 400

    # Audit log has rows for both the invite and its acceptance
    actions = [row.action for row in db_session.query(models.AuditLog).all()]
    assert "judge_invite_created" in actions
    assert "judge_invite_accepted" in actions


def test_judge_without_accepted_invite_is_denied(client):
    part_res = _register(client, "unscoped_part@hackeval.ai", "Part")
    part_headers = {"Authorization": f"Bearer {part_res.json()['access_token']}"}
    team_id = client.post("/api/teams/create", json={"name": "UnscopedTeam"}, headers=part_headers).json()["id"]

    org_headers, hack_id = _create_org_and_hackathon(client, "unscoped_org@hackeval.ai", "Unscoped Event")
    sub_res = client.post(
        "/api/submissions/upload",
        data={"hackathon_id": hack_id, "team_id": team_id, "readme_text": "# Project"},
        headers=part_headers
    )
    sub_id = sub_res.json()["id"]

    # A judge invited to a DIFFERENT hackathon, not this one
    other_org_headers, other_hack_id = _create_org_and_hackathon(client, "other_org@hackeval.ai", "A Different Event")
    invite_res = client.post(
        f"/api/hackathons/{other_hack_id}/invite-judge",
        json={"email": "outsider_judge2@hackeval.ai"},
        headers=other_org_headers
    )
    token = invite_res.json()["dev_invite_link"].split("token=")[1]
    accept_res = client.post(f"/api/auth/invite/{token}/accept", json={"full_name": "Outsider Judge", "password": "password123"})
    outsider_judge_headers = {"Authorization": f"Bearer {accept_res.json()['access_token']}"}

    # This judge is accepted for "A Different Event", not "Unscoped Event"
    denied_res = client.get(f"/api/submissions/{sub_id}", headers=outsider_judge_headers)
    assert denied_res.status_code == 403

    # An invited-and-accepted judge for THIS hackathon succeeds
    invite_res2 = client.post(
        f"/api/hackathons/{hack_id}/invite-judge",
        json={"email": "scoped_judge@hackeval.ai"},
        headers=org_headers
    )
    token2 = invite_res2.json()["dev_invite_link"].split("token=")[1]
    accept_res2 = client.post(f"/api/auth/invite/{token2}/accept", json={"full_name": "Scoped Judge", "password": "password123"})
    scoped_judge_headers = {"Authorization": f"Bearer {accept_res2.json()['access_token']}"}

    allowed_res = client.get(f"/api/submissions/{sub_id}", headers=scoped_judge_headers)
    assert allowed_res.status_code == 200


def test_rubric_update_writes_audit_log(client, db_session):
    org_headers, hack_id = _create_org_and_hackathon(client, "audit_org@hackeval.ai", "Audit Event")

    rubric_res = client.put(f"/api/hackathons/{hack_id}/rubric", json={
        "technical_complexity": 40.0, "innovation": 20.0, "ui_ux": 10.0,
        "business_impact": 10.0, "documentation": 10.0, "presentation": 10.0
    }, headers=org_headers)
    assert rubric_res.status_code == 200

    entries = db_session.query(models.AuditLog).filter(models.AuditLog.action == "rubric_updated").all()
    assert len(entries) == 1
    assert entries[0].entity_id == hack_id


def _csv_file(content: str):
    return ("judges.csv", io.BytesIO(content.encode("utf-8")), "text/csv")


def test_csv_judge_invite_bulk_upload(client, db_session):
    org_headers, hack_id = _create_org_and_hackathon(client, "csv_org@hackeval.ai", "CSV Invite Event")

    # Pre-existing account - should be skipped, not invited
    _register(client, "already_user@hackeval.ai", "Already A User", role="participant")

    csv_content = (
        "name,email\n"
        "Alice Judge,alice_judge@hackeval.ai\n"
        "Bob Judge,BOB_JUDGE@hackeval.ai\n"
        "Bob Judge Again,bob_judge@hackeval.ai\n"  # duplicate of the row above (case-insensitive)
        "Not An Email,not-an-email\n"
        "Existing User,already_user@hackeval.ai\n"
    )

    res = client.post(
        f"/api/hackathons/{hack_id}/invite-judges-csv",
        files={"file": _csv_file(csv_content)},
        headers=org_headers,
    )
    assert res.status_code == 200
    data = res.json()

    assert data["total_rows"] == 5
    assert data["invited_count"] == 2
    assert data["skipped_count"] == 3

    invited_emails = {row["email"] for row in data["invited"]}
    assert invited_emails == {"alice_judge@hackeval.ai", "bob_judge@hackeval.ai"}
    for row in data["invited"]:
        assert "dev_invite_link" in row  # no SMTP configured in tests

    skipped_reasons = {row["email"]: row["reason"] for row in data["skipped"]}
    assert skipped_reasons["bob_judge@hackeval.ai"] == "duplicate row in this file"
    assert skipped_reasons["not-an-email"] == "invalid email format"
    assert skipped_reasons["already_user@hackeval.ai"] == "a user with this email already has an account"

    invites = db_session.query(models.JudgeInvite).filter(models.JudgeInvite.hackathon_id == hack_id).all()
    assert len(invites) == 2

    created_count = db_session.query(models.AuditLog).filter(
        models.AuditLog.action == "judge_invite_created"
    ).count()
    assert created_count == 2

    # Re-uploading the same file should skip the now-pending invites rather than duplicating them
    res2 = client.post(
        f"/api/hackathons/{hack_id}/invite-judges-csv",
        files={"file": _csv_file(csv_content)},
        headers=org_headers,
    )
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["invited_count"] == 0
    assert data2["skipped_count"] == 5
    reasons2 = {row["reason"] for row in data2["skipped"]}
    assert "a pending invite already exists for this email" in reasons2


def test_csv_judge_invite_rejects_non_csv_and_missing_column(client):
    org_headers, hack_id = _create_org_and_hackathon(client, "csv_badinput_org@hackeval.ai", "CSV Bad Input Event")

    bad_ext_res = client.post(
        f"/api/hackathons/{hack_id}/invite-judges-csv",
        files={"file": ("judges.txt", io.BytesIO(b"email\nfoo@hackeval.ai\n"), "text/plain")},
        headers=org_headers,
    )
    assert bad_ext_res.status_code == 400
    assert "must be a .csv" in bad_ext_res.json()["detail"]

    no_email_col_res = client.post(
        f"/api/hackathons/{hack_id}/invite-judges-csv",
        files={"file": _csv_file("name,phone\nAlice,555-1234\n")},
        headers=org_headers,
    )
    assert no_email_col_res.status_code == 400
    assert "email" in no_email_col_res.json()["detail"]


def test_csv_judge_invite_requires_organizer_role(client):
    participant_res = _register(client, "csv_participant@hackeval.ai", "Just A Participant", role="participant")
    participant_headers = {"Authorization": f"Bearer {participant_res.json()['access_token']}"}
    org_headers, hack_id = _create_org_and_hackathon(client, "csv_perm_org@hackeval.ai", "CSV Perm Event")

    res = client.post(
        f"/api/hackathons/{hack_id}/invite-judges-csv",
        files={"file": _csv_file("email\nsomeone@hackeval.ai\n")},
        headers=participant_headers,
    )
    assert res.status_code == 403
