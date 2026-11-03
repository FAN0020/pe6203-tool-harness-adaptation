"""The admission oracle must reject misleading tool success or partial artifacts."""

import importlib.util
from pathlib import Path

import pytest

FOLDER = Path(__file__).resolve().parents[1] / "results/evidence/prefix-workflow-admission-20261101"
spec = importlib.util.spec_from_file_location("prefix_checks", FOLDER / "checks.py")
checks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)

PAGES = [
    {"index": 0, "body": "# A\n\nCANARY_A=23", "layout": "cover"},
    {"index": 1, "body": "# B\n\nCANARY_B=67", "layout": "default"},
]
TEXT = (
    "---\ntheme: dark\nlayout: cover\n---\n\n"
    + PAGES[0]["body"]
    + "\n\n---\nlayout: default\n---\n\n"
    + PAGES[1]["body"]
)


def test_accept_exact_preserved_document():
    assert checks.check_document(TEXT, PAGES, dark=True) == []


@pytest.mark.parametrize(
    "text",
    [
        TEXT.replace(PAGES[0]["body"], ""),
        TEXT + PAGES[0]["body"],
        TEXT.replace("23", "24"),
        TEXT.replace("theme: dark", "theme: default"),
        TEXT.replace(PAGES[0]["body"], "TEMP")
        .replace(PAGES[1]["body"], PAGES[0]["body"])
        .replace("TEMP", PAGES[1]["body"]),
    ],
)
def test_reject_broken_document(text):
    assert checks.check_document(text, PAGES, dark=True)


def response(pages, success=True):
    import json

    return {
        "content": [{"type": "text", "text": json.dumps({"success": success, "output": pages})}]
    }


def test_accept_native_record_state():
    assert checks.check_records(response([{**p, "content": p["body"]} for p in PAGES]), PAGES) == []


@pytest.mark.parametrize("kind", ["missing", "layout", "body", "failure", "transport"])
def test_reject_native_record_state(kind):
    rows = [{**p, "content": p["body"]} for p in PAGES]
    if kind == "missing":
        rows.pop()
    if kind == "layout":
        rows[1]["layout"] = "cover"
    if kind == "body":
        rows[0]["content"] = "missing"
    data = response(rows, success=kind != "failure")
    if kind == "transport":
        data["isError"] = True
    assert checks.check_records(data, PAGES)
