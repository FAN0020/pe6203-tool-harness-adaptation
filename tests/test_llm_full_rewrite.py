import json
from copy import deepcopy

import pytest

from integration import baselines
from integration.baseline_wrapper import validate_adapt_result


def metadata():
    return {
        "tools": [
            {
                "name": "lookup",
                "description": "Look up an entry",
                "parameters": {"type": "object"},
                "usage_rules": [],
                "routing": {"tool_name": "lookup", "server_id": "test"},
            }
        ]
    }


def completion(payload, finish="stop", usage=None):
    return {
        "choices": [{"finish_reason": finish, "message": {"content": json.dumps(payload)}}],
        "usage": usage,
    }


def valid():
    return {
        "tools": [
            {"name": "lookup", "description": "Retrieve the requested entry", "usage_rules": []}
        ]
    }


def test_rewrites_every_record_and_does_not_expose_old_or_context(mock_baseline_llm):
    data = metadata()
    before = deepcopy(data)
    knowledge, log, cost = baselines.adapt(
        {"secret_old": "OLD_SENTINEL"},
        data,
        "full_rewrite",
        {"task": "TASK_SENTINEL", "answer": "ANSWER_SENTINEL"},
    )
    sent = json.dumps(mock_baseline_llm[0][0])
    assert not any(s in sent for s in ("OLD_SENTINEL", "TASK_SENTINEL", "ANSWER_SENTINEL"))
    assert knowledge["tools"][0]["metadata"]["description"] != data["tools"][0]["description"]
    assert data == before
    assert cost["model_calls"] == 1
    assert log[0]["operation"] == "llm_full_rewrite"


@pytest.mark.parametrize(
    "defect",
    ["omitted", "duplicate", "unknown", "structural", "rules", "blank", "truncated", "json"],
)
def test_bad_output_retains_cost_and_audit(monkeypatch, tmp_path, defect):
    payload = valid()
    finish = "stop"
    if defect == "omitted":
        payload["tools"] = []
    elif defect == "duplicate":
        payload["tools"] *= 2
    elif defect == "unknown":
        payload["tools"][0]["name"] = "invented"
    elif defect == "structural":
        payload["tools"][0]["parameters"] = {}
    elif defect == "rules":
        payload["tools"][0]["usage_rules"] = ["invented rule"]
    elif defect == "blank":
        payload["tools"][0]["description"] = ""
    elif defect == "truncated":
        finish = "length"
    response = completion(payload, finish, {"prompt_tokens": 33, "completion_tokens": 7})
    if defect == "json":
        response["choices"][0]["message"]["content"] = "not JSON"
    monkeypatch.setattr(baselines, "_request_completion", lambda *args: response)
    path = tmp_path / "audit.json"
    with pytest.raises(baselines.AdaptationError) as err:
        baselines.adapt({}, metadata(), "full_rewrite", {"audit_path": str(path)})
    audit = json.loads(path.read_text())
    assert audit["status"] == "failed"
    assert audit["update_cost"]["input_tokens"] == 33
    assert audit["update_cost"]["output_tokens"] == 7
    assert audit["update_cost"]["update_operations"] == 0
    assert err.value.audit["update_cost"]["model_calls"] == 1


def test_missing_usage_stays_null(monkeypatch):
    monkeypatch.setattr(baselines, "_request_completion", lambda *args: completion(valid()))
    result = baselines.adapt({}, metadata(), "full_rewrite")
    validate_adapt_result(result)
    assert result[2]["input_tokens"] is None
    assert result[2]["output_tokens"] is None
    assert result[2]["api_cost_usd"] is None


def test_no_update_never_invokes_provider(monkeypatch):
    def forbidden(*args):
        raise AssertionError("No Update called the updater")

    monkeypatch.setattr(baselines, "_request_completion", forbidden)
    old = {"tools": [{"anything": "preserve exactly"}]}
    result = baselines.adapt(old, None, "no_update")
    assert result[0] == old
    assert result[1] == []
    assert result[2]["model_calls"] == 0


def test_real_api_requires_explicit_opt_in(tmp_path):
    with pytest.raises(baselines.AdaptationError) as err:
        baselines.adapt(
            {}, metadata(), "full_rewrite", {"audit_path": str(tmp_path / "audit.json")}
        )
    assert err.value.audit["update_cost"]["model_calls"] == 0


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -1, True])
def test_wrapper_rejects_invalid_cost(value):
    cost = dict(
        model_calls=1,
        input_tokens=None,
        output_tokens=None,
        api_cost_usd=None,
        elapsed_seconds=value,
        update_operations=1,
    )
    with pytest.raises(ValueError):
        validate_adapt_result(({}, [], cost))


@pytest.mark.parametrize("fail", [False, True])
def test_pilot_entrypoint_with_mocked_api_and_runner(
    monkeypatch, tmp_path, mock_baseline_llm, fail
):
    from pathlib import Path

    from integration import test_real_baselines as pilot

    root = Path(pilot.__file__).resolve().parents[1]
    if not (root / ".cache/mcpevol/iter3/extraction.json").is_file():
        pytest.skip("Requires local server bootstrap")
    output = tmp_path / "pilot"
    monkeypatch.setattr(
        "sys.argv",
        ["pilot", "--version", "middle", "--allow-metadata-api", "--output", str(output)],
    )
    monkeypatch.setattr(
        pilot.runner, "credentials", lambda config: ("fake", "https://fixture.invalid")
    )
    calls = []

    def run(task_id, version, strategy, seed, config):
        calls.append(strategy)
        assert config["agent"]["model"] == "deepseek-flash"
        if strategy == "full_rewrite":
            assert config["update_cost"]["tokens"] == 151
            assert config["update_cost"]["usd"] is None
        result = {
            "task_id": task_id,
            "version": version,
            "seed": seed,
            "config": config,
            "strategy": strategy,
            "status": "evaluated",
            "execution_status": "completed",
            "judge_status": "complete",
            "TF": 7,
            "PE": 8,
            "ECS": None,
            "errors": [],
        }
        # The runner contract persists observations before the pilot renders them.
        pilot.write_json(Path(config["output_dir"]) / "result.json", result)
        return {}, result

    monkeypatch.setattr(pilot.runner, "run", run)
    if fail:
        monkeypatch.setattr(
            baselines, "_request_completion", lambda *args: completion({"tools": []})
        )
        with pytest.raises(SystemExit) as exc:
            pilot.main()
        assert exc.value.code == 2
        assert calls == ["no_update"]
        assert (output / "full_rewrite/update-audit.json").is_file()
        assert not (output / "full_rewrite/knowledge.json").exists()
    else:
        pilot.main()
        assert calls == ["no_update", "full_rewrite"]
        assert len(mock_baseline_llm) == 1
        assert (output / "full_rewrite/knowledge.json").is_file()
    summary = json.loads((output / "summary.json").read_text())
    assert summary["full_rewrite_method"] == "llm_full_rewrite"
    assert summary["runs"][-1]["status"] == ("adaptation_failed" if fail else "evaluated")
    visible = (output / "report.txt").read_text()
    assert "7.00" in visible and "8.00" in visible
    assert ("adaptation_failed" in visible) == fail


def test_transient_rewrite_retry_retains_attempts_and_unknown_total_cost(monkeypatch, tmp_path):
    import httpx
    from openai import APIConnectionError

    calls = []

    def provider(messages, settings):
        calls.append(deepcopy(messages))
        if len(calls) == 1:
            raise APIConnectionError(request=httpx.Request("POST", "https://provider.invalid"))
        return completion(
            valid(), usage={"prompt_tokens": 10, "completion_tokens": 5, "cost": 0.001}
        )

    monkeypatch.setattr(baselines, "_request_completion", provider)
    path = tmp_path / "audit.json"
    _, _, cost = baselines.adapt(
        {},
        metadata(),
        "full_rewrite",
        {
            "audit_path": str(path),
            "updater": {"request_retry": {"max_retries": 1, "backoff_seconds": 0}},
        },
    )
    assert len(calls) == 2 and calls[0] == calls[1]
    assert cost["model_calls"] == 2
    assert cost["input_tokens"] is None and cost["api_cost_usd"] is None
    audit = json.loads(path.read_text())
    assert len(audit["request_retries"]) == 1
    assert audit["response"]["usage"]["cost"] == 0.001
