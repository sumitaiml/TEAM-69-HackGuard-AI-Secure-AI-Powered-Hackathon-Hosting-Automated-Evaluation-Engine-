import io
import os
import pytest

def test_submission_multi_asset_upload(client):
    # 1. Register User & Create Team
    user_res = client.post("/api/auth/register", json={
        "email": "submitter@hackguard.ai",
        "password": "password123",
        "full_name": "Sam Submitter",
        "role": "participant"
    })
    token = user_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    team_res = client.post("/api/teams/create", json={"name": "AlphaCoders"}, headers=headers)
    team_id = team_res.json()["id"]

    # 2. Register Organizer & Create Hackathon
    org_res = client.post("/api/auth/register", json={
        "email": "org2@hackguard.ai",
        "password": "password123",
        "full_name": "Org Admin",
        "role": "organizer"
    })
    org_token = org_res.json()["access_token"]
    org_headers = {"Authorization": f"Bearer {org_token}"}

    hack_res = client.post("/api/hackathons/create", json={
        "title": "AI Innovation Sprint"
    }, headers=org_headers)
    hack_id = hack_res.json()["id"]

    # 3. Submit Project with Dummy Files
    dummy_zip = ("project.zip", io.BytesIO(b"dummy zip content"), "application/zip")
    dummy_ppt = ("presentation.pptx", io.BytesIO(b"dummy ppt content"), "application/vnd.openxmlformats-officedocument.presentationml.presentation")

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

    # Check files exist on disk
    assert os.path.exists(sub_data["zip_path"])
    assert os.path.exists(sub_data["ppt_path"])

    # 4. Retrieve Submission by ID
    get_res = client.get(f"/api/submissions/{sub_data['id']}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["tech_stack"] == "React, FastAPI, Docker"

    # 5. Retrieve Submissions for Team
    team_subs_res = client.get(f"/api/submissions/team/{team_id}", headers=headers)
    assert team_subs_res.status_code == 200
    assert len(team_subs_res.json()) == 1
