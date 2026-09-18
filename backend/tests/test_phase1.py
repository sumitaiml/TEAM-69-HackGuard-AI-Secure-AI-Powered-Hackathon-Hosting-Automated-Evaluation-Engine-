import pytest

def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "online"

def test_user_registration_and_login(client):
    # Register Participant
    reg_res = client.post("/api/auth/register", json={
        "email": "participant@hackguard.ai",
        "password": "password123",
        "full_name": "Alice Dev",
        "role": "participant"
    })
    assert reg_res.status_code == 201
    data = reg_res.json()
    assert "access_token" in data
    assert data["user"]["email"] == "participant@hackguard.ai"

    # Login
    login_res = client.post("/api/auth/login", data={
        "username": "participant@hackguard.ai",
        "password": "password123"
    })
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]

    # Profile Me
    me_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["full_name"] == "Alice Dev"

def test_team_creation_and_joining(client):
    # Register Leader
    leader_res = client.post("/api/auth/register", json={
        "email": "leader@hackguard.ai",
        "password": "password123",
        "full_name": "Leader Bob",
        "role": "participant"
    })
    token_leader = leader_res.json()["access_token"]

    # Create Team
    team_res = client.post("/api/teams/create", json={"name": "CyberKnights"}, headers={"Authorization": f"Bearer {token_leader}"})
    assert team_res.status_code == 201
    team_data = team_res.json()
    invite_code = team_data["invite_code"]
    assert len(invite_code) == 6

    # Register Member
    member_res = client.post("/api/auth/register", json={
        "email": "member@hackguard.ai",
        "password": "password123",
        "full_name": "Member Charlie",
        "role": "participant"
    })
    token_member = member_res.json()["access_token"]

    # Join Team
    join_res = client.post("/api/teams/join", json={"invite_code": invite_code}, headers={"Authorization": f"Bearer {token_member}"})
    assert join_res.status_code == 200
    assert len(join_res.json()["members"]) == 2

def test_organizer_hackathon_creation_and_rubric(client):
    # Register Organizer
    org_res = client.post("/api/auth/register", json={
        "email": "organizer@hackguard.ai",
        "password": "password123",
        "full_name": "Prof. Dave",
        "role": "organizer"
    })
    token_org = org_res.json()["access_token"]

    # Create Hackathon
    hack_res = client.post("/api/hackathons/create", json={
        "title": "TechNova 2026 AI Hackathon",
        "description": "Global AI Challenge"
    }, headers={"Authorization": f"Bearer {token_org}"})
    assert hack_res.status_code == 201
    hack_id = hack_res.json()["id"]

    # Update Rubric (Valid 100%)
    rubric_res = client.put(f"/api/hackathons/{hack_id}/rubric", json={
        "technical_complexity": 30.0,
        "innovation": 20.0,
        "ui_ux": 15.0,
        "business_impact": 15.0,
        "documentation": 10.0,
        "presentation": 10.0
    }, headers={"Authorization": f"Bearer {token_org}"})
    assert rubric_res.status_code == 200

    # Update Rubric (Invalid sum != 100%)
    bad_rubric_res = client.put(f"/api/hackathons/{hack_id}/rubric", json={
        "technical_complexity": 50.0,
        "innovation": 50.0,
        "ui_ux": 50.0,
        "business_impact": 0.0,
        "documentation": 0.0,
        "presentation": 0.0
    }, headers={"Authorization": f"Bearer {token_org}"})
    assert bad_rubric_res.status_code == 400
