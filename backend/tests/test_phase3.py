import io
import zipfile

from app.celery_app import celery_app

# MinHash similarity has real statistical variance on tiny inputs (few
# shingles to sample from) - these fixtures are deliberately long enough
# (~40 lines) to give a stable, representative estimate, matching the size
# of a real (if small) submission rather than a toy one-liner.
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

# Near-duplicate of EVAL_SNIPPET_A: a handful of identifiers renamed
# (simulating copy-paste-then-rename plagiarism), structure unchanged -
# exactly the case superficial text diffing misses but AST tokenization
# should still flag as near-identical.
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

CLEAN_SNIPPET = """
def add_numbers(a, b):
    return a + b

def multiply_numbers(a, b):
    return a * b

class Calculator:
    def __init__(self):
        self.history = []

    def compute(self, op, a, b):
        if op == "add":
            value = add_numbers(a, b)
        else:
            value = multiply_numbers(a, b)
        self.history.append(value)
        return value
"""


def _zip_bytes(files: dict) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


def _register_participant_with_team(client, email, team_name):
    user_res = client.post("/api/auth/register", json={
        "email": email,
        "password": "password123",
        "full_name": "Phase3 Tester",
        "role": "participant"
    })
    token = user_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    team_res = client.post("/api/teams/create", json={"name": team_name}, headers=headers)
    return headers, team_res.json()["id"]


def _create_hackathon(client, email):
    org_res = client.post("/api/auth/register", json={
        "email": email,
        "password": "password123",
        "full_name": "Org Phase3",
        "role": "organizer"
    })
    org_headers = {"Authorization": f"Bearer {org_res.json()['access_token']}"}
    hack_res = client.post("/api/hackathons/create", json={"title": "CyberSec Challenge"}, headers=org_headers)
    return hack_res.json()["id"]


def _submit_zip(client, headers, hack_id, team_id, files: dict):
    zip_file = ("project.zip", io.BytesIO(_zip_bytes(files)), "application/zip")
    res = client.post(
        "/api/submissions/upload",
        data={"hackathon_id": hack_id, "team_id": team_id},
        files={"zip_file": zip_file},
        headers=headers
    )
    assert res.status_code == 201
    return res.json()["id"]


def _poll_task(client, headers, task_id):
    # CELERY_TASK_ALWAYS_EAGER is on in tests, so .delay() already ran the
    # task synchronously by the time the endpoint returned - one GET is
    # enough to see the final SUCCESS/FAILURE state, no real polling loop.
    res = client.get(f"/api/tasks/{task_id}", headers=headers)
    assert res.status_code == 200
    return res.json()


def test_static_analysis_flags_real_eval_usage(client):
    headers, team_id = _register_participant_with_team(client, "phase3@hackeval.ai", "SecurityTeam")
    hack_id = _create_hackathon(client, "org_phase3@hackeval.ai")
    sub_id = _submit_zip(client, headers, hack_id, team_id, {"main.py": EVAL_SNIPPET_A})

    static_res = client.post(f"/api/analysis/run-static/{sub_id}", headers=headers)
    assert static_res.status_code == 202
    task_info = _poll_task(client, headers, static_res.json()["task_id"])
    assert task_info["status"] == "SUCCESS"

    result = task_info["result"]
    assert result["status"] == "completed"
    assert "Semgrep" in result["tools_executed"]
    assert "Pylint" in result["tools_executed"]

    vulns = result["security_vulnerabilities"]
    assert len(vulns) >= 1
    eval_findings = [v for v in vulns if "eval" in v["rule_id"].lower()]
    assert len(eval_findings) >= 1
    # Proves this is real Semgrep output, not the old hardcoded simulation
    assert eval_findings[0]["rule_id"] != "security.python.eval-injection"
    assert eval_findings[0]["tool"] == "Semgrep"


def test_static_analysis_clean_code_has_no_findings(client):
    headers, team_id = _register_participant_with_team(client, "clean@hackeval.ai", "CleanTeam")
    hack_id = _create_hackathon(client, "org_clean@hackeval.ai")
    sub_id = _submit_zip(client, headers, hack_id, team_id, {"calc.py": CLEAN_SNIPPET})

    static_res = client.post(f"/api/analysis/run-static/{sub_id}", headers=headers)
    task_info = _poll_task(client, headers, static_res.json()["task_id"])

    result = task_info["result"]
    assert result["status"] == "completed"
    security_findings = [v for v in result["security_vulnerabilities"] if v["tool"] == "Semgrep"]
    assert len(security_findings) == 0


def test_static_analysis_skips_when_no_source(client):
    headers, team_id = _register_participant_with_team(client, "nosource@hackeval.ai", "NoSourceTeam")
    hack_id = _create_hackathon(client, "org_nosource@hackeval.ai")

    res = client.post(
        "/api/submissions/upload",
        data={"hackathon_id": hack_id, "team_id": team_id, "readme_text": "# Just a readme, no code"},
        headers=headers
    )
    sub_id = res.json()["id"]

    static_res = client.post(f"/api/analysis/run-static/{sub_id}", headers=headers)
    task_info = _poll_task(client, headers, static_res.json()["task_id"])

    result = task_info["result"]
    assert result["status"] == "skipped"
    assert result["tools_executed"] == []


def test_plagiarism_flags_near_duplicate_submissions(client):
    hack_id = _create_hackathon(client, "org_plag@hackeval.ai")

    headers_a, team_a = _register_participant_with_team(client, "plag_a@hackeval.ai", "TeamAlpha")
    sub_a = _submit_zip(client, headers_a, hack_id, team_a, {"main.py": EVAL_SNIPPET_A})

    headers_b, team_b = _register_participant_with_team(client, "plag_b@hackeval.ai", "TeamBeta")
    sub_b = _submit_zip(client, headers_b, hack_id, team_b, {"main.py": EVAL_SNIPPET_A_CLONE})

    headers_c, team_c = _register_participant_with_team(client, "plag_c@hackeval.ai", "TeamGamma")
    sub_c = _submit_zip(client, headers_c, hack_id, team_c, {"calc.py": CLEAN_SNIPPET})

    # Fingerprint A and C first so B has something to match against
    for sub_id, headers in [(sub_a, headers_a), (sub_c, headers_c)]:
        plag_res = client.post(f"/api/analysis/plagiarism/{sub_id}", headers=headers)
        assert plag_res.status_code == 202
        _poll_task(client, headers, plag_res.json()["task_id"])

    plag_res_b = client.post(f"/api/analysis/plagiarism/{sub_b}", headers=headers_b)
    task_info_b = _poll_task(client, headers_b, plag_res_b.json()["task_id"])
    result_b = task_info_b["result"]

    assert result_b["status"] == "completed"
    assert result_b["similarity_percentage"] > 40.0
    assert result_b["risk_level"] in ("MEDIUM", "CRITICAL")
    assert result_b["flagged_matching_submission_id"] == sub_a


def test_sandbox_endpoint_skips_unrecognized_project(client):
    # CLEAN_SNIPPET has no package.json/requirements.txt/pyproject.toml, so
    # this exercises the real (non-mocked) sandbox_runner - it should skip
    # before ever touching the Docker daemon, which is why this doesn't need
    # docker socket access to run (the api container, where pytest runs,
    # deliberately doesn't have it - only the worker does).
    headers, team_id = _register_participant_with_team(client, "sandbox@hackeval.ai", "SandboxTeam")
    hack_id = _create_hackathon(client, "org_sandbox@hackeval.ai")
    sub_id = _submit_zip(client, headers, hack_id, team_id, {"main.py": CLEAN_SNIPPET})

    sandbox_res = client.post(f"/api/analysis/sandbox/{sub_id}", headers=headers)
    assert sandbox_res.status_code == 202
    task_info = _poll_task(client, headers, sandbox_res.json()["task_id"])
    assert task_info["status"] == "SUCCESS"
    assert task_info["result"]["status"] == "skipped"
    assert task_info["result"]["build_status"] == "SKIPPED"


def test_sandbox_endpoint_mocked_successful_execution(client, monkeypatch):
    # Real sandbox execution (spawning containers via the Docker socket) is
    # only possible from the worker, not from pytest running inside the api
    # container - so the actual container-running behavior is verified
    # manually against the live stack instead, and this test proves the
    # task/endpoint plumbing correctly wires up and returns whatever
    # sandbox_runner produces.
    import app.tasks.sandbox_tasks as sandbox_tasks

    fake_result = {
        "status": "completed",
        "build_status": "SUCCESS",
        "unit_tests_passed": 4,
        "unit_tests_failed": 0,
        "execution_time_seconds": 12.3,
        "execution_logs": ["[INFO] mocked run"],
        "error": None,
    }
    monkeypatch.setattr(sandbox_tasks, "execute_in_docker_sandbox", lambda submission_id, source_dir: fake_result)

    headers, team_id = _register_participant_with_team(client, "sandbox_mock@hackeval.ai", "SandboxMockTeam")
    hack_id = _create_hackathon(client, "org_sandbox_mock@hackeval.ai")
    sub_id = _submit_zip(client, headers, hack_id, team_id, {"main.py": CLEAN_SNIPPET})

    sandbox_res = client.post(f"/api/analysis/sandbox/{sub_id}", headers=headers)
    assert sandbox_res.status_code == 202
    task_info = _poll_task(client, headers, sandbox_res.json()["task_id"])
    assert task_info["status"] == "SUCCESS"
    assert task_info["result"] == fake_result
