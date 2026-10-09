import io
import os
import zipfile
import pytest

from app.config import settings


def _make_valid_zip_bytes(inner_filename="README.md", content=b"# Test Project\n") -> bytes:
    """Both .zip and .pptx uploads are validated as real zip containers -
    this builds a minimal but structurally valid one for either case."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(inner_filename, content)
    return buf.getvalue()


def _register_participant_with_team(client, email="submitter@hackeval.ai", team_name="AlphaCoders"):
    user_res = client.post("/api/auth/register", json={
        "email": email,
        "password": "password123",
        "full_name": "Sam Submitter",
        "role": "participant"
    })
    token = user_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    team_res = client.post("/api/teams/create", json={"name": team_name}, headers=headers)
    team_id = team_res.json()["id"]
    return headers, team_id


def _create_hackathon(client, email="org2@hackeval.ai"):
    org_res = client.post("/api/auth/register", json={
        "email": email,
        "password": "password123",
        "full_name": "Org Admin",
        "role": "organizer"
    })
    org_headers = {"Authorization": f"Bearer {org_res.json()['access_token']}"}
    hack_res = client.post("/api/hackathons/create", json={"title": "AI Innovation Sprint"}, headers=org_headers)
    return hack_res.json()["id"]


def test_submission_multi_asset_upload(client):
    headers, team_id = _register_participant_with_team(client)
    hack_id = _create_hackathon(client)

    dummy_zip = ("project.zip", io.BytesIO(_make_valid_zip_bytes()), "application/zip")
    dummy_ppt = ("presentation.pptx", io.BytesIO(_make_valid_zip_bytes("slide1.xml", b"<slide/>")), "application/vnd.openxmlformats-officedocument.presentationml.presentation")

    upload_res = client.post(
        "/api/submissions/upload",
        data={
            "hackathon_id": hack_id,
            "team_id": team_id,
            "github_url": "https://github.com/alphacoders/ai-solution",
            "readme_text": "# AI Solution\nBuilt with FastAPI and React",
            "tech_stack": "React, FastAPI, Docker",
            "live_url": "https://ai-solution.vercel.app"
        },
        files={
            "zip_file": dummy_zip,
            "ppt_file": dummy_ppt
        },
        headers=headers
    )
    assert upload_res.status_code == 201
    sub_data = upload_res.json()
    assert sub_data["github_url"] == "https://github.com/alphacoders/ai-solution"
    assert sub_data["status"] == "submitted"
    assert sub_data["zip_path"] is not None
    assert sub_data["ppt_path"] is not None

    # Fixed server-side filenames, not the client-supplied ones
    assert os.path.basename(sub_data["zip_path"]) == "source.zip"
    assert os.path.basename(sub_data["ppt_path"]) == "deck.pptx"
    assert os.path.exists(sub_data["zip_path"])
    assert os.path.exists(sub_data["ppt_path"])

    # Original filenames preserved as metadata only
    assert sub_data["upload_metadata_json"]["zip"]["original_filename"] == "project.zip"
    assert sub_data["upload_metadata_json"]["ppt"]["original_filename"] == "presentation.pptx"

    # Retrieve Submission by ID (owner/team member)
    get_res = client.get(f"/api/submissions/{sub_data['id']}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["tech_stack"] == "React, FastAPI, Docker"

    # Retrieve Submissions for Team
    team_subs_res = client.get(f"/api/submissions/team/{team_id}", headers=headers)
    assert team_subs_res.status_code == 200
    assert len(team_subs_res.json()) == 1


def test_upload_rejects_invalid_zip_content(client):
    headers, team_id = _register_participant_with_team(client, "badzip@hackeval.ai", "BadZipTeam")
    hack_id = _create_hackathon(client, "org_badzip@hackeval.ai")

    fake_zip = ("project.zip", io.BytesIO(b"not actually a zip file"), "application/zip")

    res = client.post(
        "/api/submissions/upload",
        data={"hackathon_id": hack_id, "team_id": team_id},
        files={"zip_file": fake_zip},
        headers=headers
    )
    assert res.status_code == 400
    assert "not a valid zip" in res.json()["detail"]


def test_upload_rejects_disallowed_extension(client):
    headers, team_id = _register_participant_with_team(client, "badext@hackeval.ai", "BadExtTeam")
    hack_id = _create_hackathon(client, "org_badext@hackeval.ai")

    exe_file = ("payload.exe", io.BytesIO(b"MZ\x90\x00fakebinary"), "application/octet-stream")

    res = client.post(
        "/api/submissions/upload",
        data={"hackathon_id": hack_id, "team_id": team_id},
        files={"zip_file": exe_file},
        headers=headers
    )
    assert res.status_code == 400
    assert "unsupported file type" in res.json()["detail"]


def test_upload_rejects_oversized_zip(client, monkeypatch):
    monkeypatch.setattr(settings, "MAX_ZIP_SIZE_MB", 0)  # anything nonempty now exceeds the cap

    headers, team_id = _register_participant_with_team(client, "bigzip@hackeval.ai", "BigZipTeam")
    hack_id = _create_hackathon(client, "org_bigzip@hackeval.ai")

    big_zip = ("project.zip", io.BytesIO(_make_valid_zip_bytes()), "application/zip")

    res = client.post(
        "/api/submissions/upload",
        data={"hackathon_id": hack_id, "team_id": team_id},
        files={"zip_file": big_zip},
        headers=headers
    )
    assert res.status_code == 400
    assert "size limit" in res.json()["detail"]


def test_upload_video_duration_validation(client, monkeypatch):
    # The duration probe shells out to ffprobe; mocked at the service boundary
    # so this test doesn't depend on ffmpeg being installed or on generating
    # real video files.
    import app.services.upload_validation as upload_validation

    headers, team_id = _register_participant_with_team(client, "video@hackeval.ai", "VideoTeam")
    hack_id = _create_hackathon(client, "org_video@hackeval.ai")

    # Too short (10s) - outside the 180-300s window
    monkeypatch.setattr(upload_validation, "probe_video_duration_seconds", lambda path: 10.0)
    short_video = ("demo.mp4", io.BytesIO(b"fake mp4 bytes"), "video/mp4")
    res = client.post(
        "/api/submissions/upload",
        data={"hackathon_id": hack_id, "team_id": team_id},
        files={"video_file": short_video},
        headers=headers
    )
    assert res.status_code == 400
    assert "duration" in res.json()["detail"]

    # Within range (200s)
    monkeypatch.setattr(upload_validation, "probe_video_duration_seconds", lambda path: 200.0)
    good_video = ("demo.mp4", io.BytesIO(b"fake mp4 bytes"), "video/mp4")
    res = client.post(
        "/api/submissions/upload",
        data={"hackathon_id": hack_id, "team_id": team_id},
        files={"video_file": good_video},
        headers=headers
    )
    assert res.status_code == 201
    sub_data = res.json()
    assert os.path.basename(sub_data["video_path"]) == "demo.mp4"
    assert sub_data["upload_metadata_json"]["video"]["duration_seconds"] == 200.0


def test_submission_ownership_checks(client):
    headers, team_id = _register_participant_with_team(client, "owner@hackeval.ai", "OwnerTeam")
    hack_id = _create_hackathon(client, "org_owner@hackeval.ai")

    sub_res = client.post(
        "/api/submissions/upload",
        data={"hackathon_id": hack_id, "team_id": team_id, "readme_text": "# Private project"},
        headers=headers
    )
    sub_id = sub_res.json()["id"]

    # An unrelated participant (not on the team) is denied
    outsider_res = client.post("/api/auth/register", json={
        "email": "outsider@hackeval.ai",
        "password": "password123",
        "full_name": "Outsider",
        "role": "participant"
    })
    outsider_headers = {"Authorization": f"Bearer {outsider_res.json()['access_token']}"}

    assert client.get(f"/api/submissions/{sub_id}", headers=outsider_headers).status_code == 403
    assert client.get(f"/api/submissions/team/{team_id}", headers=outsider_headers).status_code == 403

    # The team owner can still access it
    assert client.get(f"/api/submissions/{sub_id}", headers=headers).status_code == 200
    assert client.get(f"/api/submissions/team/{team_id}", headers=headers).status_code == 200
