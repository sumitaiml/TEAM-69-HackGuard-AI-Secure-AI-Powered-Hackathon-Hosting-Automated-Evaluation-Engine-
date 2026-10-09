import io
import zipfile

from app import models
from app.services.gemini_client import GeminiScoreResponse
from app.services.plagiarism_explainer_agent import (
    PlagiarismExplanation,
    get_candidate_file_pairs,
    get_file_content,
)
import app.services.plagiarism_explainer_agent as plagiarism_explainer_agent_module

EVAL_SNIPPET_A = """
def process_user_input(raw):
    result = eval(raw)
    return result

def helper_one(x, y):
    total = x + y
    return total * 2

def helper_two(items):
    cleaned = []
    for item in items:
        if item is not None:
            cleaned.append(item)
    return cleaned

def helper_three(data):
    counts = {}
    for key in data:
        if key in counts:
            counts[key] += 1
        else:
            counts[key] = 1
    return counts

class RequestHandler:
    def __init__(self, config):
        self.config = config
        self.cache = {}

    def handle(self, payload):
        parsed = process_user_input(payload)
        combined = helper_one(len(str(parsed)), 10)
        return {"result": parsed, "score": combined}

    def reset(self):
        self.cache = {}
"""

EVAL_SNIPPET_A_CLONE = """
def process_user_input(raw):
    outcome = eval(raw)
    return outcome

def helper_one(x, y):
    total = x + y
    return total * 2

def helper_two(items):
    filtered = []
    for item in items:
        if item is not None:
            filtered.append(item)
    return filtered

def helper_three(data):
    tally = {}
    for key in data:
        if key in tally:
            tally[key] += 1
        else:
            tally[key] = 1
    return tally

class RequestHandler:
    def __init__(self, settings):
        self.settings = settings
        self.cache = {}

    def handle(self, payload):
        parsed = process_user_input(payload)
        combined = helper_one(len(str(parsed)), 10)
        return {"result": parsed, "score": combined}

    def reset(self):
        self.cache = {}
"""


def _zip_bytes(files: dict) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


def _register_participant_with_team(client, email, team_name):
    user_res = client.post("/api/auth/register", json={
        "email": email, "password": "password123", "full_name": "Explainer Tester", "role": "participant",
    })
    token = user_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    team_res = client.post("/api/teams/create", json={"name": team_name}, headers=headers)
    return headers, team_res.json()["id"]


def _create_hackathon(client, email):
    org_res = client.post("/api/auth/register", json={
        "email": email, "password": "password123", "full_name": "Org Explainer", "role": "organizer",
    })
    org_headers = {"Authorization": f"Bearer {org_res.json()['access_token']}"}
    hack_res = client.post("/api/hackathons/create", json={"title": "ExplainerHack"}, headers=org_headers)
    return hack_res.json()["id"]


def _submit_zip(client, headers, hack_id, team_id, files: dict):
    zip_file = ("project.zip", io.BytesIO(_zip_bytes(files)), "application/zip")
    res = client.post(
        "/api/submissions/upload",
        data={"hackathon_id": hack_id, "team_id": team_id},
        files={"zip_file": zip_file},
        headers=headers,
    )
    assert res.status_code == 201
    return res.json()["id"]


def _make_submission(db_session, submission_id, hackathon_id, team_id):
    db_session.add(models.Submission(
        id=submission_id, team_id=team_id, hackathon_id=hackathon_id, status="completed",
    ))


def test_get_candidate_file_pairs_uses_real_sql(client, db_session):
    # PlagiarismFileFingerprint.submission_id is a real foreign key - create
    # actual Hackathon/Team/Submission rows rather than weakening the schema
    # to accommodate a sloppier test.
    hack_id = _create_hackathon(client, "org_candidatepairs@hackeval.ai")
    _, team_a = _register_participant_with_team(client, "candidatepairs_a@hackeval.ai", "TeamCandidateA")
    _, team_b = _register_participant_with_team(client, "candidatepairs_b@hackeval.ai", "TeamCandidateB")
    _make_submission(db_session, "sub-a", hack_id, team_a)
    _make_submission(db_session, "sub-b", hack_id, team_b)
    db_session.commit()

    db_session.add(models.PlagiarismFileFingerprint(
        submission_id="sub-a", file_path="main.py", minhash_signature=[1, 2, 3, 4, 5],
    ))
    db_session.add(models.PlagiarismFileFingerprint(
        submission_id="sub-a", file_path="utils.py", minhash_signature=[100, 101, 102, 103, 104],
    ))
    db_session.add(models.PlagiarismFileFingerprint(
        submission_id="sub-b", file_path="app.py", minhash_signature=[1, 2, 3, 999, 999],  # 3/5 overlap with main.py
    ))
    db_session.add(models.PlagiarismFileFingerprint(
        submission_id="sub-b", file_path="other.py", minhash_signature=[500, 501, 502, 503, 504],  # no overlap
    ))
    db_session.commit()

    pairs = get_candidate_file_pairs(db_session, "sub-a", "sub-b")

    assert len(pairs) == 1
    assert pairs[0]["file_a"] == "main.py"
    assert pairs[0]["file_b"] == "app.py"
    assert pairs[0]["similarity"] >= 0.5


def test_get_file_content_blocks_path_traversal(tmp_path):
    (tmp_path / "safe.txt").write_text("real content")
    result = get_file_content(str(tmp_path), "../../../etc/passwd")
    assert "outside" in result


def test_get_file_content_reads_real_file(tmp_path):
    (tmp_path / "safe.txt").write_text("real content here")
    result = get_file_content(str(tmp_path), "safe.txt")
    assert result == "real content here"


def test_full_pipeline_triggers_explainer_only_for_flagged_submission(client, monkeypatch):
    import app.services.ai_evaluation as ai_evaluation_module
    fake_gemini_result = GeminiScoreResponse(
        innovation_score=70.0, ui_ux_score=70.0, business_impact_score=70.0,
        documentation_quality_score=70.0, presentation_quality_score=70.0,
        feedback=["ok"], improvement_suggestions=["ok"],
    )
    monkeypatch.setattr(ai_evaluation_module.gemini_client, "score_submission", lambda **kwargs: fake_gemini_result)

    fake_explanation = PlagiarismExplanation(
        verdict="probable_copying",
        explanation="Both files implement near-identical request handling logic with only cosmetic renames.",
        cited_file_pairs=["main.py <-> main.py"],
    )
    monkeypatch.setattr(plagiarism_explainer_agent_module, "call_structured_gemini", lambda prompt, schema: fake_explanation)

    hack_id = _create_hackathon(client, "org_explainer@hackeval.ai")

    headers_a, team_a = _register_participant_with_team(client, "explainer_a@hackeval.ai", "TeamExplainerA")
    sub_a = _submit_zip(client, headers_a, hack_id, team_a, {"main.py": EVAL_SNIPPET_A})
    task_a = client.post(f"/api/evaluation/evaluate/{sub_a}", headers=headers_a)
    assert task_a.status_code == 202
    report_a = client.get(f"/api/evaluation/report/{sub_a}", headers=headers_a).json()
    # First submission - nothing to compare against yet, should not be flagged.
    assert report_a["plagiarism_json"]["risk_level"] == "LOW"
    assert report_a["plagiarism_json"].get("explanation") is None

    headers_b, team_b = _register_participant_with_team(client, "explainer_b@hackeval.ai", "TeamExplainerB")
    sub_b = _submit_zip(client, headers_b, hack_id, team_b, {"main.py": EVAL_SNIPPET_A_CLONE})
    task_b = client.post(f"/api/evaluation/evaluate/{sub_b}", headers=headers_b)
    assert task_b.status_code == 202
    report_b = client.get(f"/api/evaluation/report/{sub_b}", headers=headers_b).json()

    assert report_b["plagiarism_json"]["risk_level"] in ("MEDIUM", "CRITICAL")
    explanation = report_b["plagiarism_json"]["explanation"]
    assert explanation["verdict"] == "probable_copying"
    assert "request handling" in explanation["explanation"]
