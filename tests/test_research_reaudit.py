import json

from scripts.research_reaudit import judge_scores, normalized_properties


def test_historical_optional_unknown_is_not_a_new_requirement():
    p = normalized_properties({"findings": [
        {"property": "charts", "status": "pass"},
        {"property": "summary", "status": "unknown"},
        {"property": "Rendered appearance", "status": "unknown"},
    ]})
    assert p == {"charts": "pass", "summary": "unknown"}
    assert not all(v == "pass" for v in p.values())


def test_boolean_synthetic_review_preserves_failure():
    assert normalized_properties({"properties": {"records": True, "links": False}}) == {
        "records": "pass", "links": "fail"}


def test_duplicate_judge_slot_cannot_count_as_complete(tmp_path):
    (tmp_path / "EVAL").mkdir()
    slots = [{"slot": 1, "attempt": 1, "result": {}}] * 5
    (tmp_path / "EVAL/1.json").write_text(json.dumps({"eval_result": {"runs": slots}}))
    means, count, errors = judge_scores(tmp_path, 1, {"judge_status": "complete"})
    assert "five_slots_missing_or_duplicated" in errors
    assert count == 0 and means == {"TF": None, "PE": None}
