import pytest

def test_phase4_evaluation_override_and_leaderboard(client):
    # 1. Register Users (Participant, Organizer, Judge)
    part_res = client.post("/api/auth/register", json={
        "email": "phase4_part@hackguard.ai",
        "password": "password123",
        "full_name": "Phase4 Participant",
        "role": "participant"
    })
    part_token = part_res.json()["access_token"]
    part_headers = {"Authorization": f"Bearer {part_token}"}

    org_res = client.post("/api/auth/register", json={
        "email": "phase4_org@hackguard.ai",
        "password": "password123",
        "full_name": "Phase4 Organizer",
        "role": "organizer"
    })
    org_token = org_res.json()["access_token"]
    org_headers = {"Authorization": f"Bearer {org_token}"}

    judge_res = client.post("/api/auth/register", json={
        "email": "phase4_judge@hackguard.ai",
        "password": "password123",
        "full_name": "Judge Alan",
        "role": "judge"
    })
    judge_token = judge_res.json()["access_token"]
    judge_headers = {"Authorization": f"Bearer {judge_token}"}

    # 2. Setup Team & Hackathon
    team_res = client.post("/api/teams/create", json={"name": "NeuralNetTeam"}, headers=part_headers)
    team_id = team_res.json()["id"]

    hack_res = client.post("/api/hackathons/create", json={"title": "AI World Cup 2026"}, headers=org_headers)
    hack_id = hack_res.json()["id"]

    # 3. Submit Project
    sub_res = client.post(
        "/api/submissions/upload",
        data={
            "hackathon_id": hack_id,
            "team_id": team_id,
            "github_url": "https://github.com/neuralnet/solution",
            "readme_text": "# NeuralNet Solution\nHigh performance deep learning pipeline.",
            "tech_stack": "PyTorch, FastAPI, React"
        },
        headers=part_headers
    )
    sub_id = sub_res.json()["id"]

    # 4. Trigger AI Multimodal Evaluation
    eval_res = client.post(f"/api/evaluation/evaluate/{sub_id}", headers=part_headers)
    assert eval_res.status_code == 201
    report_data = eval_res.json()
    report_id = report_data["id"]
    assert report_data["final_score"] > 0.0
    assert "ai_scores_json" in report_data
    assert "whisper_transcript" in report_data["ai_scores_json"]

    # 5. Fetch Evaluation Report
    get_report_res = client.get(f"/api/evaluation/report/{sub_id}", headers=part_headers)
    assert get_report_res.status_code == 200
    assert get_report_res.json()["id"] == report_id

    # 6. Judge Score Override (Invalid without justification)
    bad_override_res = client.post(
        f"/api/evaluation/override/{report_id}",
        json={
            "parameter_scores": {
                "technical_complexity": 100.0,
                "innovation": 100.0,
                "ui_ux": 100.0,
                "business_impact": 100.0,
                "documentation": 100.0,
                "presentation": 100.0
            },
            "justification_notes": ""  # Empty justification should fail
        },
        headers=judge_headers
    )
    assert bad_override_res.status_code == 400

    # 7. Judge Score Override (Valid with 100% parameter scores and justification)
    good_override_res = client.post(
        f"/api/evaluation/override/{report_id}",
        json={
            "parameter_scores": {
                "technical_complexity": 100.0,
                "innovation": 100.0,
                "ui_ux": 100.0,
                "business_impact": 100.0,
                "documentation": 100.0,
                "presentation": 100.0
            },
            "justification_notes": "Outstanding architecture design and flawless live demonstration.",
            "judge_comments": "Verified and approved for top rank."
        },
        headers=judge_headers
    )
    assert good_override_res.status_code == 200
    assert good_override_res.json()["final_score"] == 100.0
    assert good_override_res.json()["judge_override_json"]["justification"] == "Outstanding architecture design and flawless live demonstration."

    # 8. Check Leaderboard
    leader_res = client.get(f"/api/evaluation/leaderboard/{hack_id}")
    assert leader_res.status_code == 200
    lb_data = leader_res.json()
    assert len(lb_data) == 1
    assert lb_data[0]["rank"] == 1
    assert lb_data[0]["score"] == 100.0
    assert lb_data[0]["team_name"] == "NeuralNetTeam"
