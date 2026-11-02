"""Check supplemental coverage and preserve V6's structured request contract."""

from collections import Counter
from types import SimpleNamespace

from scripts import eval_five_task_supplement as supplement


def test_only_missing_tasks_and_explicit_versions_have_balanced_repeats():
    cells = supplement.make_cells()
    assert len(cells) == 90
    assert len({c["id"] for c in cells}) == 90
    assert {c["task_id"] for c in cells} == {430, 90}
    assert {c["arm"] for c in cells} == {"no_update", "full_rewrite", "v1", "v2", "v6"}
    assert set(Counter((c["task_id"], c["stage"], c["arm"]) for c in cells).values()) == {3}
    assert all(c["strategy"] == (c["arm"] if c["arm"] in ("no_update", "full_rewrite") else "selective_patch") for c in cells)


def test_structured_updater_does_not_downgrade_v6_schema(monkeypatch, tmp_path):
    captured = {}
    class Client:
        def __init__(self, **kwargs):
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def create(self, **kwargs):
            captured.update(kwargs)
            response = {"id": "offline-test", "model": supplement.common.MODEL,
                        "provider": "DigitalOcean", "usage": {"cost": 0.001}}
            return SimpleNamespace(model_dump=lambda **_: response)
    monkeypatch.setattr(supplement, "OpenAI", Client)
    monkeypatch.setattr(supplement.runner, "credentials", lambda _: ("offline-test", "https://example.test"))
    schema = {"type": "json_schema", "json_schema": {"name": "test", "strict": True, "schema": {}}}
    guard = supplement.Guard(tmp_path, 2)
    guard.structured_updater([], {"allow_metadata_api": True, "temperature": 0,
                                 "max_tokens": 20, "timeout": 30, "response_format": schema})
    assert captured["response_format"] == schema
    assert captured["extra_body"] == supplement.common.ROUTING
    assert len(guard.rows) == 1 and guard.rows[0]["usd"] == 0.001
