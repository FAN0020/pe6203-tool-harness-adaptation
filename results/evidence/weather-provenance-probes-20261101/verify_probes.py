"""Offline archive, frozen-call and weather provenance/readiness verification."""
import hashlib
import json
import re
import tarfile
from pathlib import Path

FOLDER = Path(__file__).resolve().parent
PREFIX = "results/evidence/weather-provenance-probes-20261101/"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def verify():
    manifest = json.loads((FOLDER / "archive-manifest.json").read_text())
    archive = FOLDER / "probe-and-source.tar.gz"
    assert digest(archive.read_bytes()) == manifest["archive_sha256"]
    with tarfile.open(archive) as tar:
        names = tar.getnames()
        assert len(names) == len(set(names)) == manifest["file_count"]
        assert set(names) == {row["path"] for row in manifest["files"]}
        files = {name: tar.extractfile(name).read() for name in names}
    for row in manifest["files"]:
        assert digest(files[row["path"]]) == row["sha256"]
    plan_path = "experiments/weather-provenance-probes-v1.json"
    plan = json.loads(files[plan_path])
    before = json.loads(files[PREFIX + "preexecution.json"])
    assert before["plan_sha256"] == digest(files[plan_path])
    assert before["collector_sha256"] == digest(files[PREFIX + "run_probes.py"])
    for row in plan["source"]:
        assert digest(files[row["path"]]) == row["sha256"]
    observations = json.loads(files[PREFIX + "observations.json"])
    assert len(observations) == plan["tool_calls"] == 7
    forecasts = []
    for stage in plan["stages"]:
        catalog = json.loads(files[PREFIX + f"{stage}-catalog.json"])
        names = {tool["name"] for tool in catalog["tools"]}
        assert ("get-weather-advice" in names) == (stage != "early")
        rows = [row for row in observations if row["stage"] == stage]
        assert len(rows) == len(plan["calls"][stage])
        advice = []
        for index, (row, call) in enumerate(zip(rows, plan["calls"][stage], strict=True), 1):
            assert row == json.loads(files[PREFIX + f"{stage}-{index:02d}.json"])
            assert all(row[key] == call[key] for key in call)
            assert not row.get("exception") and not row["result"].get("isError")
            text = "\n".join(c.get("text", "") for c in row["result"]["content"])
            if call["kind"] == "synthetic_provenance":
                assert "26°C" in text
                advice.append(re.sub(r"\(12,(-20|140)\)", "COORD", text))
            else:
                assert text.startswith("Forecast for 34.05, -118.24:")
                assert text.count("Temperature:") == text.count("Wind:") == 14
                assert "Unknown" not in text and "Light Rain" in text
                forecasts.append(text)
        if advice:
            assert len(advice) == 2 and advice[0] == advice[1]
    assert len(set(forecasts)) == 1
    review = json.loads(files[PREFIX + "mechanism-review.json"])
    assert digest(forecasts[0].encode()) == review["facts"]["forecast_text_sha256"]
    for stage in ["iter3", "iter5"]:
        source = files[f".cache/mcpevol/{stage}/node_modules/mcp-weather-demo/build/index.js"].decode()
        advice_source = source.split("async function getWeatherAdvice(data) {", 1)[1].split(
            "async function makeNWSRequest(url)", 1)[0]
        assert "Math.round(30 - Math.abs(data.latitude) / 3)" in advice_source
        assert "fetch(" not in advice_source and "Date(" not in advice_source
    result = {"archive_files_verified": len(files), "tool_calls": 7, "catalog_calls": 3,
              "native_provenance_pass": True, "real_forecast_readiness_pass": True,
              "agent_efficacy": "not tested", "model_calls": 0, "model_usd": 0}
    print(json.dumps(result))
    (FOLDER / "verification.json").write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    verify()
