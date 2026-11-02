import json

import pytest

from pe6203.benchmark import load_task


def setup_tasks(tmp_path):
    data = tmp_path / "src/custom/data/test_cases"
    data.mkdir(parents=True)
    (data / "chosen_idx.json").write_text('{"samples":[{"idx":235}]}')
    (data / "test_cases.json").write_text(
        json.dumps(
            [
                {
                    "idx": 235,
                    "question": "original",
                    "servers": {"chart": ["plot"]},
                    "answer": "PRIVATE REFERENCE",
                }
            ]
        )
    )
    extension = tmp_path / "extension.json"
    extension.write_text(
        json.dumps(
            {
                "idx": 900001,
                "extension_id": "ext-log-dev-v1",
                "dataset_kind": "controlled_synthetic_extension",
                "question": "Read the supplied logs",
                "servers": {"code": ["run"]},
            }
        )
    )
    return extension


def test_extension_load_is_separate_and_does_not_override_original(tmp_path):
    extension = setup_tasks(tmp_path)
    task = load_task(tmp_path, 900001, extension)
    assert task["idx"] == 900001
    assert task["dataset_kind"] == "controlled_synthetic_extension"
    assert task["extension_id"] == "ext-log-dev-v1"
    assert load_task(tmp_path, 235, extension) == {
        "idx": 235,
        "question": "original",
        "servers": {"chart": ["plot"]},
    }


@pytest.mark.parametrize(
    "field,value",
    [
        ("idx", 235),
        ("idx", 377),
        ("extension_id", "task377"),
        ("dataset_kind", "benchmark"),
        ("oracle", {"total": 42}),
        ("servers", {}),
        ("question", ""),
    ],
)
def test_extension_rejects_collision_unmarked_or_answer_bearing_manifest(tmp_path, field, value):
    extension = setup_tasks(tmp_path)
    content = json.loads(extension.read_text())
    content[field] = value
    extension.write_text(json.dumps(content))
    with pytest.raises(ValueError):
        load_task(tmp_path, 900001, extension)


def test_unregistered_extension_cannot_bypass_benchmark_selection(tmp_path):
    setup_tasks(tmp_path)
    with pytest.raises(ValueError, match="selected 201"):
        load_task(tmp_path, 900001)
