"""Common CLI/runner contracts for the shared LLM updater; all responses are fake."""

import copy
import json

import pytest
from test_baselines import snapshot

from integration import baselines as llm
from pe6203.baselines import adapt, write_adaptation
from pe6203.cli import main
from pe6203.runner import prepare_tools


def inputs(tmp_path, target=None):
    old_path, new_path = tmp_path / "early.json", tmp_path / "late.json"
    old_path.write_text(json.dumps(snapshot()))
    new_path.write_text(json.dumps(target or snapshot("late")))
    return old_path, new_path


def test_duplicate_native_names_and_immutable_fields(mock_baseline_llm):
    old, target = snapshot(), snapshot("late")
    for envelope in (old, target):
        other = copy.deepcopy(envelope["tools"][0])
        other.update(server_id="other", tool_id="other::old_tool")
        other["routing"]["server_id"] = "other"
        other["usage_rules"] = ["Only read local files"]
        other["output_schema"] = {"type": "string"}
        envelope["tools"].append(other)
    original = copy.deepcopy(target)
    knowledge, log, cost = adapt(
        old, target, "full_rewrite", {"task": "SECRET_TASK", "answer": "SECRET_ANSWER"}
    )
    assert cost["calls"] == 1 and cost["total_tokens"] == 151
    assert cost["usd"] is None
    assert log[0]["rebuilt_tool_ids"] == [t["tool_id"] for t in target["tools"]]
    assert len(prepare_tools(knowledge["tools"], "full_rewrite", "namespaced")[0]) == 2
    sent = mock_baseline_llm[0][0][-1]["content"]
    assert "SECRET_TASK" not in sent and "SECRET_ANSWER" not in sent
    for actual, expected in zip(knowledge["tools"], target["tools"], strict=True):
        assert actual["description"] == "Rewritten: " + expected["description"]
        assert {k: v for k, v in actual.items() if k != "description"} == {
            k: v for k, v in expected.items() if k != "description"
        }
    assert target == original


def test_common_cli_calls_shared_llm_and_passes_configuration(
    tmp_path, monkeypatch, mock_baseline_llm
):
    old, target = inputs(tmp_path)
    output = tmp_path / "adaptation"
    config = tmp_path / "updater.json"
    config.write_text(json.dumps({"model": "fixture-model", "timeout": 19, "max_tokens": 123}))
    monkeypatch.setattr(
        "sys.argv",
        [
            "pe6203",
            "adapt",
            "--strategy",
            "full_rewrite",
            "--old-knowledge",
            str(old),
            "--new-metadata",
            str(target),
            "--output",
            str(output),
            "--updater-config",
            str(config),
            "--allow-metadata-api",
        ],
    )
    assert main() == 0
    settings = mock_baseline_llm[0][1]
    assert settings["model"] == "fixture-model" and settings["timeout"] == 19
    assert settings["max_tokens"] == 123 and settings["allow_metadata_api"] is True
    artifact = json.loads((output / "adaptation.json").read_text())
    assert artifact["formal_llm_rewrite"] is True and artifact["status"] == "validated"
    assert artifact["cost"]["method"] == "llm_full_rewrite"
    assert (output / "updater-audit.json").is_file()
    knowledge = json.loads((output / "knowledge.json").read_text())
    prepare_tools(knowledge["tools"], "full_rewrite")


@pytest.mark.parametrize("failure", ["truncated", "omitted", "schema", "provider", "json"])
def test_failure_has_no_fallback_and_retains_cost_and_audit(tmp_path, monkeypatch, failure):
    old, target = inputs(tmp_path)
    output = tmp_path / "failed"
    calls = []

    def complete(messages, settings):
        calls.append(messages)
        if failure == "provider":
            raise RuntimeError("Provider failed")
        tool = json.loads(messages[-1]["content"])["tools"][0]
        item = {"name": tool["name"], "description": "Rewritten", "usage_rules": []}
        if failure == "schema":
            item["parameters"] = {}
        payload = {"tools": [] if failure == "omitted" else [item]}
        return {
            "choices": [
                {
                    "finish_reason": "length" if failure == "truncated" else "stop",
                    "message": {"content": "invalid" if failure == "json" else json.dumps(payload)},
                }
            ],
            "usage": {"prompt_tokens": 17, "completion_tokens": 4, "cost": 0.001},
        }

    monkeypatch.setattr(llm, "_request_completion", complete)
    with pytest.raises(llm.AdaptationError):
        write_adaptation(old, target, "full_rewrite", output)
    artifact = json.loads((output / "adaptation.json").read_text())
    assert len(calls) == 1 and not (output / "knowledge.json").exists()
    assert artifact["status"] == "failed" and artifact["formal_llm_rewrite"] is True
    assert artifact["cost"]["calls"] == 1
    assert artifact["cost"]["update_operations"] == 0
    assert artifact["cost"]["total_tokens"] == (None if failure == "provider" else 21)
    assert artifact["cost"]["usd"] == (None if failure == "provider" else 0.001)
    assert json.loads((output / "updater-audit.json").read_text())["status"] == "failed"


def test_common_entry_does_not_call_provider_without_opt_in(tmp_path, monkeypatch):
    import integration.baselines

    def forbidden(*args, **kwargs):
        pytest.fail("Created provider client without consent")

    monkeypatch.setattr(integration.baselines, "OpenAI", forbidden)
    old, target = inputs(tmp_path)
    output = tmp_path / "no-consent"
    with pytest.raises(llm.AdaptationError):
        write_adaptation(old, target, "full_rewrite", output)
    artifact = json.loads((output / "adaptation.json").read_text())
    assert artifact["cost"]["calls"] == 0 and artifact["cost"]["total_tokens"] is None
    assert not (output / "knowledge.json").exists()


def test_missing_usage_not_counted_as_zero(monkeypatch):
    def complete(messages, settings):
        tools = json.loads(messages[-1]["content"])["tools"]
        return {
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {
                        "content": json.dumps(
                            {
                                "tools": [
                                    {
                                        "name": t["name"],
                                        "description": "Rewritten",
                                        "usage_rules": [],
                                    }
                                    for t in tools
                                ],
                            }
                        )
                    },
                }
            ]
        }

    monkeypatch.setattr(llm, "_request_completion", complete)
    _, _, cost = adapt(snapshot(), snapshot("late"), "full_rewrite")
    for field in ("prompt_tokens", "completion_tokens", "total_tokens", "usd"):
        assert cost[field] is None


def test_no_update_never_calls_llm_or_reads_target(monkeypatch):
    monkeypatch.setattr(llm, "adapt", lambda *a: pytest.fail("No Update used LLM"))
    knowledge, log, cost = adapt(snapshot(), None, "no_update")
    assert knowledge == snapshot() and log == [] and cost["calls"] == 0


def test_inline_credentials_rejected_before_request(mock_baseline_llm):
    with pytest.raises(ValueError, match="environment variable"):
        adapt(snapshot(), snapshot("late"), "full_rewrite", {"updater": {"api_key": "secret"}})
    assert mock_baseline_llm == []


def test_config_file_cannot_enable_metadata_api_without_cli_flag(tmp_path, monkeypatch):
    old, target = inputs(tmp_path)
    config = tmp_path / "updater.json"
    config.write_text(json.dumps({"allow_metadata_api": True}))
    output = tmp_path / "not-authorized"
    monkeypatch.setattr(llm, "OpenAI", lambda **kw: pytest.fail("Unauthorized model client"))
    monkeypatch.setattr(
        "sys.argv",
        [
            "pe6203",
            "adapt",
            "--strategy",
            "full_rewrite",
            "--old-knowledge",
            str(old),
            "--new-metadata",
            str(target),
            "--output",
            str(output),
            "--updater-config",
            str(config),
        ],
    )
    assert main() == 2
    artifact = json.loads((output / "adaptation.json").read_text())
    assert artifact["cost"]["calls"] == 0 and artifact["status"] == "failed"
