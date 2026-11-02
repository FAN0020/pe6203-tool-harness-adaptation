"""Compatibility checks for the combined Selective Patch version entry points."""

import copy
import os
import subprocess
import sys
from pathlib import Path

import pytest
from test_contract import record

from integration import baselines as provider
from pe6203.baselines import adapt
from pe6203.capability import fingerprint

ROOT = Path(__file__).resolve().parents[1]
MODES = ["deterministic_v1", "hybrid_v2", "hybrid_v3", "hybrid_v5", "hybrid_v6"]


def catalog():
    return {
        "schema_version": "1.0",
        "benchmark_commit": "version-integration-test",
        "version": "early",
        "tools": [record()],
    }


@pytest.mark.parametrize("mode", MODES)
def test_each_mode_handles_unchanged_knowledge_without_a_provider_call(mode, monkeypatch):
    def unexpected(*args, **kwargs):
        raise AssertionError("Unchanged knowledge must not request a model")

    monkeypatch.setattr(provider, "_request_completion", unexpected)
    old = catalog()
    context = {"selective_mode": mode}
    if mode == "hybrid_v3":
        tool = old["tools"][0]
        context["capability_evidence"] = {
            "version": "capability-evidence-v1",
            "entries": [
                {
                    "tool_id": tool["tool_id"],
                    "tool_fingerprint": fingerprint(tool),
                    "kind": "catalog",
                    "quote": tool["description"],
                }
            ],
        }
    knowledge, _, cost = adapt(old, copy.deepcopy(old), "selective_patch", context)
    assert {t["tool_id"] for t in knowledge["tools"]} == {t["tool_id"] for t in old["tools"]}
    assert cost.get("calls", 0) == 0


def test_default_preserves_existing_main_without_implicit_model_use(monkeypatch):
    def unexpected(*args, **kwargs):
        raise AssertionError("Existing main commands must not gain a model dependency")

    monkeypatch.setattr(provider, "_request_completion", unexpected)
    old = catalog()
    target = copy.deepcopy(old)
    target["version"] = "late"
    target["tools"][0]["version"] = "late"
    target["tools"][0]["description"] = "Current declared tool description"
    knowledge, _, cost = adapt(old, target, "selective_patch")
    assert knowledge["tools"][0]["description"] == target["tools"][0]["description"]
    assert cost["method"] == "deterministic_diff_selective_patch"
    assert cost.get("calls", 0) == 0


@pytest.mark.parametrize(
    "command",
    ["run-artifact-arm", "freeze-artifact-plan", "collect-v5-probes", "run-v5", "run-v6"],
)
def test_version_commands_coexist_in_the_public_cli(command):
    result = subprocess.run(
        [sys.executable, "-m", "pe6203.cli", command, "--help"],
        cwd=ROOT,
        env={**os.environ, "PYTHONPATH": os.pathsep.join([str(ROOT / "src"), str(ROOT)])},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert command in result.stdout
