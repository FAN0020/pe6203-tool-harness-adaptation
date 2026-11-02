"""Independent checks catch fixture/oracle contamination and wrong event semantics."""

import importlib.util
import json
import re
from collections import Counter
from pathlib import Path

import pytest

SOURCE = Path(__file__).parents[1] / "experiments/extensions/magicui-log-dashboard-v1/generate.py"


def test_frozen_generator_has_independent_correct_oracle_and_no_answer_in_input(tmp_path):
    spec = importlib.util.spec_from_file_location("extension_generator", SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.generate(tmp_path / "one", 314159)
    module.generate(tmp_path / "two", 314159)
    one = tmp_path / "one"
    assert (one / "manifest.json").read_bytes() == (tmp_path / "two/manifest.json").read_bytes()
    assert {p.suffix for p in (one / "input").rglob("*") if p.is_file()} == {".log"}
    totals = Counter()
    for file in (one / "input/logs").glob("*.log"):
        for line in file.read_text().splitlines():
            match = re.match(r"^\[(\d{4}-\d{2}-\d{2})T[^]]+\] \[(\w+)\]", line)
            if match:
                totals[match[1]] += int(match[2] == "ERROR")
    answer = json.loads((one / "oracle.json").read_text())
    assert answer["daily"] == [{"date": d, "errors": n} for d, n in sorted(totals.items())]
    assert answer["total_errors"] == sum(totals.values())
    assert answer["days_covered"] == 7
    assert answer["daily"][3] == {"date": "2026-02-05", "errors": 0}
    assert len(totals) == 7 and max(totals.values()) > 0
    with pytest.raises(FileExistsError):
        module.generate(one, 9)
