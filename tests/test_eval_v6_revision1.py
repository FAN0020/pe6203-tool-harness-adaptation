"""Paid-cost accounting must distinguish completion-only repair from judging."""

from types import SimpleNamespace

import pytest

from scripts import eval_v6_revision1 as revision


@pytest.mark.asyncio
async def test_completion_only_artifact_repair_remains_agent_cost(monkeypatch, tmp_path):
    class Client:
        def __init__(self, **kwargs):
            async def create(**body):
                return SimpleNamespace(model_dump=lambda **_: {
                    "id": "offline-test", "model": revision.common.MODEL,
                    "provider": "DigitalOcean", "usage": {"cost": 0.001}})
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=create))
    monkeypatch.setattr(revision, "AsyncOpenAI", Client)
    guard = revision.Guard(tmp_path, 1)
    client = guard.async_client()
    await client.chat.completions.create(
        model=revision.common.MODEL, extra_body=revision.common.ROUTING,
        messages=[], response_format={"type": "json_schema", "json_schema": {"name": "artifact_v1_delivery"}})
    assert guard.rows[0]["phase"] == "agent"


def test_full_task_set_excludes_no_original_task():
    assert set(revision.TASKS) == {133, 235, 283, 430, 90}
