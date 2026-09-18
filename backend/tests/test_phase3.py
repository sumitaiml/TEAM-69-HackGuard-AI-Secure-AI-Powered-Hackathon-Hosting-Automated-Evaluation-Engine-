import pytest

def test_phase3_analysis_and_sandbox(client):
    # 1. Register Participant & Create Team
    user_res = client.post("/api/auth/register", json={
        "email": "phase3@hackguard.ai",
        "password": "password123",
        "full_name": "Phase3 Tester",
        "role": "participant"
    })
    token = user_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    team_res = client.post("/api/teams/create", json={"name": "SecurityTeam"}, headers=headers)
    team_id = team_res.json()["id"]

    # 2. Register Organizer & Create Hackathon
    org_res = client.post("/api/auth/register", json={
        "email": "org_phase3@hackguard.ai",
        "password": "password123",
        "full_name": "Org Phase3",
        "role": "organizer"
    })
    org_token = org_res.json()["access_token"]
    org_headers = {"Authorization": f"Bearer {org_token}"}

    hack_res = client.post("/api/hackathons/create", json={"title": "CyberSec Challenge"}, headers=org_headers)
    assert hack_res.status_code == 201
    hack_id = hack_res.json()["id"]

    # 3. Submit Project
    sub_res = client.post(
        "/api/submissions/upload",
        data={
            "hackathon_id": hack_id,
            "team_id": team_id,
            "github_url": "https://github.com/securityteam/hackguard",
            "readme_text": "# HackGuard App\ndef eval(user_input): pass"
        },
        headers=headers
    )
    assert sub_res.status_code == 201
    sub_id = sub_res.json()["id"]

    # 4. Test Static Analysis Endpoint
    static_res = client.post(f"/api/analysis/run-static/{sub_id}", headers=headers)
    assert static_res.status_code == 200
    static_data = static_res.json()
    assert "code_quality_score" in static_data
    assert "tools_executed" in static_data
    assert len(static_data["security_vulnerabilities"]) >= 1  # Should flag eval()

    # 5. Test Plagiarism Detection Endpoint
    plag_res = client.post(f"/api/analysis/plagiarism/{hack_id}?target_submission_id={sub_id}", headers=headers)
    assert plag_res.status_code == 200
    plag_data = plag_res.json()
    assert "similarity_percentage" in plag_data
    assert "risk_level" in plag_data

    # 6. Test Docker Sandbox Execution Endpoint
    sandbox_res = client.post(f"/api/analysis/sandbox/{sub_id}", headers=headers)
    assert sandbox_res.status_code == 200
    sb_data = sandbox_res.json()
    assert sb_data["build_status"] == "SUCCESS"
    assert sb_data["unit_tests_passed"] == 12
    assert "execution_logs" in sb_data
