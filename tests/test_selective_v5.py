"""Synthetic V5 regression cases; scripted responses are not model evaluations."""

import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest
from test_hybrid_selective import catalogs as catalogs
from test_hybrid_selective import response

from integration import baselines as provider
from pe6203 import execution_v5
from pe6203.baselines import adapt, write_adaptation
from pe6203.benchmark import read_json, write_json
from pe6203.evidence_v5 import VERSION, check_result, fingerprint, load_bundle, registry
from pe6203.rules_v5 import render_rule
from pe6203.selective_v5 import HybridPatchError, adapt_result


def refs(payload, identity="server::display"):
    result = []
    for key, value in payload["evidence_registry"].items():
        if (
            value["kind"] == "catalog"
            and value["field"] == "description"
            and value["side"] == "target"
            and value["tool_id"] in {identity, "server::fetch_balance"}
        ):
            result.append(key)
    return result


def reply(payload, *, action="update", kind="guidance"):
    if payload.get("phase") == "scope_screen":
        eligible = [row["tool_id"] for row in payload["directory"]]
        return {
            "screened_tool_ids": eligible,
            "candidates": [
                {
                    "tool_id": "server::display",
                    "classification": "potential_impact",
                    "basis": [payload["changes"][0]["change_id"]],
                    "reason": "The balance units affect an implicit consumer.",
                }
            ]
            if "server::display" in eligible
            else [],
        }
    decisions = []
    for row in payload["records"]:
        identity = row["tool_id"]
        affected = identity == "server::display"
        decision = {
            "tool_id": identity,
            "action": action if affected else "keep",
            "reason": "Units may affect display" if affected else "Unrelated",
            "basis": row["basis"] if affected else [],
            "evidence_ids": refs(payload) if affected else [],
        }
        if affected and action == "update":
            decision.update(
                retain_rule_indices=[],
                rules=[
                    {
                        "kind": kind,
                        "text": "Convert cents to dollars before display.",
                        "evidence_ids": refs(payload),
                    }
                ],
            )
        decisions.append(decision)
    return {"decisions": decisions}


def install_llm(monkeypatch, factory=reply):
    requests = []

    def complete(messages, settings):
        payload = json.loads(messages[-1]["content"])
        requests.append(copy.deepcopy(payload))
        return response(factory(payload))

    monkeypatch.setattr(provider, "_request_completion", complete)
    return requests


def ctx(**kwargs):
    return {"selective_mode": "hybrid_v5", "updater": {"allow_metadata_api": True}, **kwargs}


def bundle(tmp_path, target, *, kind="probe", stage=None, result=None):
    tool = target["tools"][0]
    subject = {
        "tool_id": tool["tool_id"],
        "tool_fingerprint": fingerprint(tool),
        "stage": stage or target["version"],
        "benchmark_commit": target["benchmark_commit"],
    }
    content = {
        **subject,
        "arguments": {"amount": 1},
        "result": {"isError": False} if result is None else result,
        "check": {"pointer": "/isError", "operator": "equals", "expected": True},
    }
    file = tmp_path / ("exchange.json" if kind == "probe" else "source.txt")
    file.write_text(
        json.dumps(content) if kind == "probe" else "return value; // no enforcement here\n"
    )
    manifest = tmp_path / "evidence.json"
    write_json(
        manifest,
        {
            "version": VERSION,
            "entries": [
                {
                    **subject,
                    "kind": kind,
                    "path": file.name,
                    "sha256": hashlib.sha256(file.read_bytes()).hexdigest(),
                }
            ],
        },
    )
    return manifest


def test_light_screen_local_edit_and_no_metadata_change(catalogs, monkeypatch):
    old, target = catalogs
    before = copy.deepcopy(catalogs)
    install_llm(monkeypatch)
    result = adapt_result(old, target, ctx())
    assert result["audit"]["pipeline_version"] == "hybrid_v5"
    assert result["audit"]["reviewed_tool_ids"] == ["server::display"]
    assert result["audit"]["screened_tool_ids"] == ["server::display", "server::unchanged"]
    assert result["audit"]["scope_plan"]["program_completed_tool_ids"] == ["server::fetch_balance"]
    assert result["knowledge"]["tools"][0]["description"] == target["tools"][0]["description"]
    assert result["knowledge"]["tools"][2] == old["tools"][2]
    assert result["knowledge"]["tools"][1]["usage_rules"][0].startswith("Unverified LLM guidance")
    assert (
        result["audit"]["semantic_patches"][0]["withdrawn_rules"][0]["text"]
        == old["tools"][1]["usage_rules"][0]
    )
    assert result["cost"]["calls"] == 2
    assert result["audit"]["validation"]["behavioral_guarantees_admitted"] is False
    assert catalogs == before


def test_unknown_withdraws_stale_rules_but_keeps_schema_update(catalogs, monkeypatch):
    old, target = catalogs
    target["tools"][1]["parameters"]["required"].append("new_flag")
    target["tools"][1]["parameters"]["properties"]["new_flag"] = {"type": "boolean"}
    install_llm(monkeypatch, lambda p: reply(p, action="unresolved"))
    result = adapt_result(old, target, ctx())
    updated = result["knowledge"]["tools"][1]
    assert updated["parameters"] == target["tools"][1]["parameters"]
    assert old["tools"][1]["usage_rules"][0] not in updated["usage_rules"]
    assert updated["usage_rules"][0].startswith("Unknown semantic impact")
    assert result["audit"]["unresolved_items"] and result["cost"]["calls"] == 2


@pytest.mark.parametrize(
    "corruption",
    ["invent_id", "free_guarantee", "metadata_edit", "missing_record", "retain_invalid"],
)
def test_invalid_model_output_never_publishes(catalogs, monkeypatch, tmp_path, corruption):
    def corrupt(payload):
        data = reply(payload)
        if payload.get("phase") == "local_semantic_review":
            row = next(r for r in data["decisions"] if r["action"] == "update")
            if corruption == "invent_id":
                row["evidence_ids"] = ["invented"]
            elif corruption == "free_guarantee":
                row["rules"][0]["kind"] = "behavior_guarantee"
            elif corruption == "metadata_edit":
                row["parameters"] = {}
            elif corruption == "retain_invalid":
                row["retain_rule_indices"] = [99]
        elif corruption == "missing_record":
            data["screened_tool_ids"].pop()
        return data

    install_llm(monkeypatch, corrupt)
    old, target = catalogs
    write_json(tmp_path / "old.json", old)
    write_json(tmp_path / "target.json", target)
    with pytest.raises(HybridPatchError):
        write_adaptation(
            tmp_path / "old.json",
            tmp_path / "target.json",
            "selective_patch",
            tmp_path / "out",
            ctx(),
        )
    assert not (tmp_path / "out/knowledge.json").exists()
    assert read_json(tmp_path / "out/adaptation.json")["status"] == "failed"
    assert read_json(tmp_path / "out/updater-audit.json")["cost"]["calls"] >= 1


def test_ids_restore_literals_and_cannot_promote_catalog_to_behavior(catalogs, tmp_path):
    old, target = catalogs
    sources = registry(old, target, load_bundle(bundle(tmp_path, target), target))
    catalog_id = next(
        k
        for k, v in sources.items()
        if v["kind"] == "catalog" and v["side"] == "target" and v["field"] == "description"
    )
    rule = {"kind": "documentation", "text": "", "evidence_ids": [catalog_id]}
    assert target["tools"][0]["description"] in render_rule(rule, sources)
    with pytest.raises(ValueError, match="recorded probe"):
        render_rule({**rule, "kind": "probe_observation"}, sources)
    probe_id = next(k for k, v in sources.items() if v["kind"] == "probe")
    rendered = render_rule(
        {**rule, "kind": "probe_observation", "evidence_ids": [probe_id]}, sources
    )
    assert '"matched": false' in rendered and "only to this exchange" in rendered


@pytest.mark.parametrize(
    "change", ["hash", "stage", "fingerprint", "traversal", "extra_answer", "schema_arguments"]
)
def test_bundle_rejects_stale_tampered_or_unscoped_evidence(catalogs, tmp_path, change):
    _, target = catalogs
    manifest = bundle(tmp_path, target)
    data = read_json(manifest)
    row = data["entries"][0]
    if change == "hash":
        row["sha256"] = "0" * 64
    elif change == "stage":
        row["stage"] = "early"
    elif change == "fingerprint":
        row["tool_fingerprint"] = "stale"
    elif change == "traversal":
        row["path"] = "../exchange.json"
    elif change == "schema_arguments":
        file = tmp_path / row["path"]
        exchange = read_json(file)
        exchange["arguments"] = {"unknown": "not allowed"}
        write_json(file, exchange)
        row["sha256"] = hashlib.sha256(file.read_bytes()).hexdigest()
    else:
        row["answer"] = "forbidden"
    write_json(manifest, data)
    with pytest.raises(ValueError):
        load_bundle(manifest, target)


def test_no_change_no_evidence_no_api_and_baseline_unchanged(catalogs, monkeypatch):
    old, _ = catalogs
    install_llm(monkeypatch, lambda _: pytest.fail("Unexpected updater call"))
    result = adapt_result(old, copy.deepcopy(old), ctx())
    assert result["knowledge"] == old and result["cost"]["calls"] == 0
    nu, _, cost = adapt(old, {"not": "metadata"}, "no_update", ctx())
    assert nu == old and cost["calls"] == 0
    fr, _, cost = adapt(old, old, "full_rewrite", ctx())
    assert fr == old and cost["calls"] == 0


@pytest.mark.parametrize("budget", [{"max_calls": 1}, {"max_request_chars": 1000}])
def test_insufficient_budget_never_silently_skips_review(catalogs, monkeypatch, budget):
    requests = install_llm(monkeypatch)
    with pytest.raises(HybridPatchError):
        adapt_result(*catalogs, ctx(patch_budget=budget))
    assert len(requests) == (1 if "max_calls" in budget else 0)


def test_multibatch_review_preserves_full_coverage(catalogs, monkeypatch):
    requests = install_llm(monkeypatch)
    result = adapt_result(*catalogs, ctx(patch_budget={"review_batch_size": 1}))
    assert result["audit"]["reviewed_tool_ids"] == ["server::display"]
    assert len(result["audit"]["screened_tool_ids"]) == 2
    assert result["cost"]["calls"] == len(requests) == 2


def test_evidence_only_event_triggers_review_without_fake_catalog_diff(
    catalogs, monkeypatch, tmp_path
):
    old, _ = catalogs
    install_llm(monkeypatch)
    result = adapt_result(old, copy.deepcopy(old), ctx(evidence_bundle=str(bundle(tmp_path, old))))
    assert result["audit"]["diff"]["changed"] == []
    assert result["cost"]["calls"] == 2
    assert any(
        c["kind"] == "independent_evidence"
        for c in result["audit"]["review_basis_changes"].values()
    )


def test_evidence_only_event_binds_target_stage(catalogs, monkeypatch, tmp_path):
    old, target = catalogs
    target["tools"][0]["description"] = old["tools"][0]["description"]
    install_llm(monkeypatch)
    result = adapt_result(old, target, ctx(evidence_bundle=str(bundle(tmp_path, target))))
    assert result["knowledge"]["version"] == "late"
    assert result["audit"]["diff"]["changed"] == []


@pytest.mark.asyncio
async def test_probe_collection_freezes_actions_and_records_mismatched_expectation(
    catalogs, monkeypatch, tmp_path
):
    from contextlib import asynccontextmanager
    from types import SimpleNamespace

    from pe6203 import evidence_v5, transport
    from pe6203.evidence_v5 import collect_probes

    _, target = catalogs
    calls = []

    async def call_tool(name, arguments):
        calls.append((name, copy.deepcopy(arguments)))
        return SimpleNamespace(model_dump=lambda **_: {"isError": False})

    @asynccontextmanager
    async def sessions(*args):
        yield {"server": SimpleNamespace(call_tool=call_tool)}

    async def snapshot(*args):
        return target

    monkeypatch.setattr(transport, "sessions", sessions)
    monkeypatch.setattr(transport, "snapshot", snapshot)
    monkeypatch.setattr(
        evidence_v5,
        "source",
        lambda _: (
            {"commit": target["benchmark_commit"], "stages": {target["version"]: {}}},
            tmp_path,
        ),
    )
    write_json(tmp_path / "catalog.json", target)
    write_json(
        tmp_path / "plan.json",
        {
            "version": "selective-probes-v5",
            "reviewed": True,
            "catalog": "catalog.json",
            "timeout_seconds": 2,
            "probes": [
                {
                    "tool_id": target["tools"][0]["tool_id"],
                    "arguments": {"amount": 1},
                    "check": {"pointer": "/isError", "operator": "equals", "expected": True},
                }
            ],
        },
    )
    audit = await collect_probes(tmp_path, tmp_path / "plan.json", tmp_path / "probes")
    assert calls == [("fetch_balance", {"amount": 1})]
    assert audit["calls"][0]["observation"]["matched"] is False
    assert (
        load_bundle(tmp_path / "probes/evidence.json", target)["entries"][0]["observation"][
            "matched"
        ]
        is False
    )


@pytest.mark.artifact_isolation
@pytest.mark.asyncio
async def test_v5_real_functional_failure_sdk_repair_and_exact_isolated_retest(catalogs, tmp_path):
    import os

    import httpx
    from openai import AsyncOpenAI
    from test_artifact_validation import BAD, GOOD, answer, protocol
    from test_runner import completion

    from pe6203.artifact_validation import DockerBackend, settings
    from pe6203.runner import agent_loop, prepare_tools

    image = os.environ.get("PE6203_ARTIFACT_IMAGE")
    if not image:
        pytest.skip("No reviewed local pinned Python image; real isolated repair not tested")
    config = settings(protocol(image=image, max_repair_tokens=128))
    if not DockerBackend(config).available():
        pytest.skip("Docker/local reviewed image unavailable")
    old, _ = catalogs
    tools, routes = prepare_tools(old["tools"], "selective_patch")
    workspace = tmp_path / "run/workspace"
    workspace.mkdir(parents=True)
    requests, events = [], []

    def handler(request):
        body = json.loads(request.content)
        requests.append(body)
        if len(requests) == 2:
            feedback = json.loads(body["messages"][-1]["content"])
            assert feedback["attempt"]["status"] == "test_failed"
            assert feedback["attempt"]["isolated_execution"] is True
            assert feedback["source"] == BAD and "tools" not in body
        return completion(
            {"role": "assistant", "content": answer(BAD if len(requests) == 1 else GOOD)}
        )

    async with AsyncOpenAI(
        api_key="scripted-test-only",
        base_url="http://fixture.local/v1",
        max_retries=0,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    ) as client:
        result = await agent_loop(
            client,
            {},
            tools,
            routes,
            "Synthetic normalize function",
            workspace,
            {
                "max_rounds": 1,
                "agent": {
                    "model": "scripted-not-a-real-model",
                    "temperature": 0,
                    "max_completion_tokens": 128,
                },
                "artifact_validation": config,
            },
            5,
            events.append,
        )
    audit = result["artifact_validation"]
    assert [a["status"] for a in audit["attempts"]] == ["test_failed", "passed_finite_tests"]
    assert all(a["isolated_execution"] for a in audit["attempts"])
    assert audit["accepted_artifact"]["sha256"] == hashlib.sha256(GOOD.encode()).hexdigest()
    assert result["completion_origin"] == "artifact_repair"
    assert len(requests) == 2 and result["usage"]["total_tokens"] == 30


@pytest.mark.parametrize("kwargs", [{"task": "x"}, {"answers": []}, {"judge_scores": [10]}])
def test_task_data_forbidden(catalogs, kwargs):
    with pytest.raises(ValueError, match="forbidden"):
        adapt_result(*catalogs, ctx(**kwargs))


def test_check_result_is_bounded_typed_and_missing_is_not_null_match():
    assert not check_result({}, {"pointer": "/absent", "operator": "equals", "expected": None})[
        "matched"
    ]
    assert not check_result(
        {"value": True}, {"pointer": "/value", "operator": "equals", "expected": 1}
    )["matched"]
    assert check_result(
        {"text": "invalid expression"},
        {"pointer": "/text", "operator": "contains", "expected": "invalid"},
    )["matched"]


def test_v5_execution_requires_exact_mode_and_explicit_scope(tmp_path, monkeypatch):
    from test_artifact_validation import protocol

    write_json(tmp_path / "adapt.json", {"pipeline_version": "hybrid_v5", "status": "validated"})
    write_json(tmp_path / "config.json", {})
    write_json(tmp_path / "protocol.json", protocol())
    captured = []
    monkeypatch.setattr(
        execution_v5, "run", lambda *args: captured.append(args) or ({}, {"status": "evaluated"})
    )
    args = (
        tmp_path,
        999,
        "late",
        0,
        tmp_path / "config.json",
        tmp_path / "adapt.json",
        tmp_path / "run",
    )
    execution_v5.run_v5(*args, artifact_protocol=tmp_path / "protocol.json")
    config = captured[0][-1]
    assert config["artifact_validation"]["version"] == "artifact-v1"
    assert config["v5_protocol"]["knowledge_update_effect_isolated"] is False
    assert captured[0][2] == "selective_patch"
    with pytest.raises(ValueError, match="Declare either"):
        execution_v5.run_v5(*args)
    write_json(tmp_path / "adapt.json", {"pipeline_version": "hybrid_v2", "status": "validated"})
    with pytest.raises(ValueError, match="hybrid_v5"):
        execution_v5.run_v5(*args, non_python_deliverable=True)


def test_public_cli_v5_no_change_without_paid_calls(catalogs, tmp_path):
    old, _ = catalogs
    write_json(tmp_path / "old.json", old)
    process = subprocess.run(
        [
            sys.executable,
            "-m",
            "pe6203.cli",
            "adapt",
            "--strategy",
            "selective_patch",
            "--selective-mode",
            "hybrid_v5",
            "--old-knowledge",
            str(tmp_path / "old.json"),
            "--new-metadata",
            str(tmp_path / "old.json"),
            "--output",
            str(tmp_path / "out"),
        ],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
    )
    assert process.returncode == 0, process.stderr
    artifact = read_json(tmp_path / "out/adaptation.json")
    assert artifact["pipeline_version"] == "hybrid_v5" and artifact["cost"]["calls"] == 0
