import pytest

from app.services.gemini_client import GeminiScoreResponse


def _poll_task(client, headers, task_id):
    res = client.get(f"/api/tasks/{task_id}", headers=headers)
    assert res.status_code == 200
    return res.json()


def test_phase4_evaluation_override_and_leaderboard(client, monkeypatch):
    # Gemini is mocked at the service boundary - this test verifies the
    # evaluation pipeline's plumbing (real static analysis, plagiarism,
    # sandbox-skip, async task orchestration, override, leaderboard), not
    # Gemini's own output quality, which was verified manually against the
    # live API while building gemini_client.py.
    import app.services.ai_evaluation as ai_evaluation_module
    fake_gemini_result = GeminiScoreResponse(
        innovation_score=85.0,
        ui_ux_score=88.0,
        business_impact_score=80.0,
        documentation_quality_score=90.0,
        presentation_quality_score=82.0,
        feedback=["Solid architecture and clear problem framing."],
        improvement_suggestions=["Add more automated test coverage."],
    )
    monkeypatch.setattr(
        ai_evaluation_module.gemini_client, "score_submission",
        lambda **kwargs: fake_gemini_result
    )

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

    # 2. Setup Team & Hackathon
    team_res = client.post("/api/teams/create", json={"name": "NeuralNetTeam"}, headers=part_headers)
    team_id = team_res.json()["id"]

    hack_res = client.post("/api/hackathons/create", json={"title": "AI World Cup 2026"}, headers=org_headers)
    hack_id = hack_res.json()["id"]

    # Judges are invited by the organizer, not self-registered - accept the
    # invite (dev_invite_link, since no SMTP is configured in tests) to get
    # a real judge account.
    invite_res = client.post(
        f"/api/hackathons/{hack_id}/invite-judge",
        json={"email": "phase4_judge@hackguard.ai"},
        headers=org_headers
    )
    assert invite_res.status_code == 201
    invite_token = invite_res.json()["dev_invite_link"].split("token=")[1]
    accept_res = client.post(
        f"/api/auth/invite/{invite_token}/accept",
        json={"full_name": "Judge Alan", "password": "password123"}
    )
    assert accept_res.status_code == 200
    judge_token = accept_res.json()["access_token"]
    judge_headers = {"Authorization": f"Bearer {judge_token}"}

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

    # 4. Trigger AI Multimodal Evaluation (async - enqueue + poll)
    eval_res = client.post(f"/api/evaluation/evaluate/{sub_id}", headers=part_headers)
    assert eval_res.status_code == 202
    task_info = _poll_task(client, part_headers, eval_res.json()["task_id"])
    assert task_info["status"] == "SUCCESS"
    assert task_info["result"]["final_score"] > 0.0
    assert task_info["result"]["ai_evaluation_degraded"] is False
    report_id = task_info["result"]["report_id"]

    # 5. Fetch Evaluation Report
    get_report_res = client.get(f"/api/evaluation/report/{sub_id}", headers=part_headers)
    assert get_report_res.status_code == 200
    report_data = get_report_res.json()
    assert report_data["id"] == report_id
    assert report_data["final_score"] > 0.0
    assert "ai_scores_json" in report_data
    assert "whisper_transcript" in report_data["ai_scores_json"]
    assert report_data["ai_scores_json"]["ai_feedback"] == fake_gemini_result.feedback

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


def test_evaluation_degrades_gracefully_when_gemini_fails(client, monkeypatch):
    # A total Gemini outage (all model candidates exhausted) must not fail
    # the whole evaluation - the real static/plagiarism/sandbox results
    # still get saved, with a documented degraded flag for judges to see.
    import app.services.ai_evaluation as ai_evaluation_module
    monkeypatch.setattr(
        ai_evaluation_module.gemini_client, "score_submission",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("all Gemini model candidates failed"))
    )

    part_res = client.post("/api/auth/register", json={
        "email": "degraded_part@hackguard.ai", "password": "password123",
        "full_name": "Degraded Participant", "role": "participant"
    })
    part_headers = {"Authorization": f"Bearer {part_res.json()['access_token']}"}

    org_res = client.post("/api/auth/register", json={
        "email": "degraded_org@hackguard.ai", "password": "password123",
        "full_name": "Degraded Organizer", "role": "organizer"
    })
    org_headers = {"Authorization": f"Bearer {org_res.json()['access_token']}"}

    team_res = client.post("/api/teams/create", json={"name": "DegradedTeam"}, headers=part_headers)
    team_id = team_res.json()["id"]
    hack_res = client.post("/api/hackathons/create", json={"title": "Degraded Mode Event"}, headers=org_headers)
    hack_id = hack_res.json()["id"]

    sub_res = client.post(
        "/api/submissions/upload",
        data={"hackathon_id": hack_id, "team_id": team_id, "readme_text": "# A project\nSome details here."},
        headers=part_headers
    )
    sub_id = sub_res.json()["id"]

    eval_res = client.post(f"/api/evaluation/evaluate/{sub_id}", headers=part_headers)
    assert eval_res.status_code == 202
    task_info = _poll_task(client, part_headers, eval_res.json()["task_id"])

    assert task_info["status"] == "SUCCESS"
    assert task_info["result"]["ai_evaluation_degraded"] is True

    report = client.get(f"/api/evaluation/report/{sub_id}", headers=part_headers).json()
    assert report["ai_scores_json"]["ai_evaluation_degraded"] is True
    assert "degraded_reason" in report["ai_scores_json"]
    # Partial success, not all-or-nothing: a final score still exists
    assert report["final_score"] > 0.0
