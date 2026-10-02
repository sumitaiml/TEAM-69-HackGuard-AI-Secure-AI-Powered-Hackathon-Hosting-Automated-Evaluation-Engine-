from app.services.ai_code_detection import run_ai_code_detection_check

# Deliberately mimics the scaffolding style common in LLM-generated code:
# heavy, templated comments, boilerplate phrasing, and generic variable
# names reused across every function instead of domain-specific vocabulary.
BOILERPLATE_LIKE_CODE = '''
# This function is responsible for processing the input data.
def process_data(data):
    # Here is the implementation of the processing logic.
    result = data
    return result

# This function is responsible for handling the response.
def handle_response(data):
    # In this code, we transform the input into a result.
    result = data
    value = result
    return value

# This function is responsible for computing the output.
def compute_output(data):
    # Here is the implementation of the computation.
    temp = data
    result = temp
    return result
'''

# Deliberately mimics messy, domain-specific, sparsely-commented hackathon
# code written under time pressure - low comment density, no boilerplate
# phrasing, varied and specific identifier names.
HUMAN_LIKE_CODE = '''
def calc_leaderboard_rank(scores, team_id):
    sorted_scores = sorted(scores.items(), key=lambda kv: -kv[1])
    for idx, (tid, _) in enumerate(sorted_scores):
        if tid == team_id:
            return idx + 1
    return -1

def merge_submission_assets(zip_path, ppt_path, video_path):
    bundle = {"zip": zip_path, "ppt": ppt_path, "video": video_path}
    missing = [k for k, v in bundle.items() if not v]
    return bundle, missing

class SubmissionValidator:
    def __init__(self, max_video_mb):
        self.max_video_mb = max_video_mb

    def check_video_size(self, size_bytes):
        return (size_bytes / (1024 * 1024)) <= self.max_video_mb
'''


def test_flags_boilerplate_style_code_as_higher_risk(tmp_path):
    (tmp_path / "main.py").write_text(BOILERPLATE_LIKE_CODE)

    result = run_ai_code_detection_check(str(tmp_path))

    assert result["status"] == "completed"
    assert result["risk_level"] in ("MEDIUM", "HIGH")
    assert result["signals"]["boilerplate_phrase_hits"] > 0
    assert result["signals"]["generic_identifier_ratio"] > 0.3


def test_human_like_code_scores_lower_risk(tmp_path):
    (tmp_path / "main.py").write_text(HUMAN_LIKE_CODE)

    result = run_ai_code_detection_check(str(tmp_path))

    assert result["status"] == "completed"
    assert result["risk_level"] == "LOW"
    assert result["signals"]["boilerplate_phrase_hits"] == 0


def test_boilerplate_code_scores_higher_than_human_code(tmp_path):
    boilerplate_dir = tmp_path / "boilerplate"
    boilerplate_dir.mkdir()
    (boilerplate_dir / "main.py").write_text(BOILERPLATE_LIKE_CODE)

    human_dir = tmp_path / "human"
    human_dir.mkdir()
    (human_dir / "main.py").write_text(HUMAN_LIKE_CODE)

    boilerplate_result = run_ai_code_detection_check(str(boilerplate_dir))
    human_result = run_ai_code_detection_check(str(human_dir))

    assert boilerplate_result["estimated_ai_usage_percentage"] > human_result["estimated_ai_usage_percentage"]


def test_skips_when_no_source_dir():
    result = run_ai_code_detection_check(None)
    assert result["status"] == "skipped"
    assert result["risk_level"] == "UNKNOWN"


def test_skips_when_no_recognized_source_files(tmp_path):
    (tmp_path / "README.md").write_text("# Just a readme")

    result = run_ai_code_detection_check(str(tmp_path))

    assert result["status"] == "skipped"
