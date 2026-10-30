import io
import zipfile
import pytest
from app import models
from app.auth import get_password_hash, create_access_token


def _make_valid_zip_bytes(inner_filename="README.md", content=b"# Test\n") -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(inner_filename, content)
    return buf.getvalue()


def _register_user(client, email: str, role: str):
    res = client.post("/api/auth/register", json={
        "email": email,
        "password": "password123",
        "full_name": f"{role.capitalize()} User",
        "role": role,
    })
    assert res.status_code == 201
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_judge(db_session, email="test_judge@hackeval.ai"):
    judge = models.User(
        email=email,
        hashed_password=get_password_hash("password123"),
        full_name="Test Judge",
        role="judge",
        is_verified=True,
    )
    db_session.add(judge)
    db_session.commit()
    db_session.refresh(judge)
    token = create_access_token(data={"sub": judge.id, "role": "judge"})
    return {"Authorization": f"Bearer {token}"}


def _create_hackathon(client, org_headers, title="Delete Test Hackathon"):
    res = client.post("/api/hackathons/create", json={"title": title}, headers=org_headers)
    assert res.status_code == 201
    return res.json()["id"]


def _create_submission(client, part_headers, hackathon_id: str, team_name="TeamDeleters"):
    team_res = client.post("/api/teams/create", json={"name": team_name}, headers=part_headers)
    assert team_res.status_code == 201
    team_id = team_res.json()["id"]

    zip_bytes = _make_valid_zip_bytes()
    files = {"zip_file": ("code.zip", io.BytesIO(zip_bytes), "application/zip")}
    data = {
        "hackathon_id": hackathon_id,
        "team_id": team_id,
        "readme_text": "# Sample Readme",
        "tech_stack": "python, fastapi",
    }
    sub_res = client.post("/api/submissions/upload", data=data, files=files, headers=part_headers)
    assert sub_res.status_code == 201
    return sub_res.json()["id"], team_id


def test_participant_cannot_delete_hackathon(client):
    org_headers = _register_user(client, "org_test1@hackeval.ai", "organizer")
    part_headers = _register_user(client, "part_test1@hackeval.ai", "participant")
    hack_id = _create_hackathon(client, org_headers)

    res = client.delete(f"/api/hackathons/{hack_id}", headers=part_headers)
    assert res.status_code == 403


def test_participant_cannot_delete_submission(client):
    org_headers = _register_user(client, "org_test2@hackeval.ai", "organizer")
    part_headers = _register_user(client, "part_test2@hackeval.ai", "participant")
    hack_id = _create_hackathon(client, org_headers)
    sub_id, _ = _create_submission(client, part_headers, hack_id, team_name="TeamPart")

    res = client.delete(f"/api/submissions/{sub_id}", headers=part_headers)
    assert res.status_code == 403


def test_delete_nonexistent_hackathon_and_submission(client):
    org_headers = _register_user(client, "org_test3@hackeval.ai", "organizer")
    res1 = client.delete("/api/hackathons/non-existent-hack-id", headers=org_headers)
    assert res1.status_code == 404

    res2 = client.delete("/api/submissions/non-existent-sub-id", headers=org_headers)
    assert res2.status_code == 404


def test_judge_and_organizer_can_delete_submission(client, db_session):
    org_headers = _register_user(client, "org_test4@hackeval.ai", "organizer")
    judge_headers = _create_judge(db_session, "judge_test4@hackeval.ai")
    part_headers = _register_user(client, "part_test4@hackeval.ai", "participant")

    hack_id = _create_hackathon(client, org_headers)
    sub_id1, _ = _create_submission(client, part_headers, hack_id, team_name="Team1")
    sub_id2, _ = _create_submission(client, part_headers, hack_id, team_name="Team2")

    # Judge deletes submission 1
    del_res1 = client.delete(f"/api/submissions/{sub_id1}", headers=judge_headers)
    assert del_res1.status_code == 204
    assert db_session.query(models.Submission).filter_by(id=sub_id1).first() is None

    # Organizer deletes submission 2
    del_res2 = client.delete(f"/api/submissions/{sub_id2}", headers=org_headers)
    assert del_res2.status_code == 204
    assert db_session.query(models.Submission).filter_by(id=sub_id2).first() is None


def test_organizer_can_delete_hackathon_cascade(client, db_session):
    org_headers = _register_user(client, "org_test5@hackeval.ai", "organizer")
    part_headers = _register_user(client, "part_test5@hackeval.ai", "participant")

    hack_id = _create_hackathon(client, org_headers, title="Cascade Hackathon")
    sub_id, _ = _create_submission(client, part_headers, hack_id, team_name="CascadeTeam")

    # Invite a judge to test invite deletion as well
    invite_res = client.post(
        f"/api/hackathons/{hack_id}/invite-judge",
        json={"email": "invited_judge@hackeval.ai"},
        headers=org_headers,
    )
    assert invite_res.status_code == 201

    # Organizer deletes hackathon
    res = client.delete(f"/api/hackathons/{hack_id}", headers=org_headers)
    assert res.status_code == 204

    # Assert hackathon, submission, judge invites are all wiped
    assert db_session.query(models.Hackathon).filter_by(id=hack_id).first() is None
    assert db_session.query(models.Submission).filter_by(id=sub_id).first() is None
    assert db_session.query(models.JudgeInvite).filter_by(hackathon_id=hack_id).first() is None

    # Assert audit log entry
    audit = db_session.query(models.AuditLog).filter_by(entity_id=hack_id, action="hackathon_deleted").first()
    assert audit is not None


def test_judge_can_delete_hackathon(client, db_session):
    org_headers = _register_user(client, "org_test6@hackeval.ai", "organizer")
    judge_headers = _create_judge(db_session, "judge_test6@hackeval.ai")

    hack_id = _create_hackathon(client, org_headers, title="Judge Delete Target")

    # Judge deletes hackathon
    res = client.delete(f"/api/hackathons/{hack_id}", headers=judge_headers)
    assert res.status_code == 204
    assert db_session.query(models.Hackathon).filter_by(id=hack_id).first() is None
