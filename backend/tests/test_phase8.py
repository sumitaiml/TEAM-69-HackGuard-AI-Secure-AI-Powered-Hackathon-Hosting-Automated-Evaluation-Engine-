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
