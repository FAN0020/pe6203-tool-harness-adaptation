"""Offline admission verification, including retained failed measurements."""
import hashlib
import json
import tarfile
from pathlib import Path

from checks import check_document, check_records, unpack
from generate_cases import generate

FOLDER = Path(__file__).resolve().parent


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(name):
    return json.loads((FOLDER / name).read_text())


def main():
    pack = read("native-input-packaging.json")
    assert sha((FOLDER / pack["archive"]).read_bytes()) == pack["sha256"]
    with tarfile.open(FOLDER / pack["archive"]) as tar:
        files = {m.name: tar.extractfile(m).read() for m in tar if m.isfile()}
    assert {k: sha(v) for k, v in files.items()} == pack["files"] == read("preexecution.json")["files"]
    cases = read("cases.json")
    assert cases == generate()
    rows = read("observations.json")
    assert len(rows) == 40
    for stage in ("middle", "late"):
        for name in ("train", "heldout"):
            subset = [r for r in rows if r["stage"] == stage and r["case"] == name]
            assert len(subset) == (9 if name == "train" else 11)
            count, dark, previous = 0, False, None
            for row in subset:
                inner = unpack(row["result"])
                if row["tool"] in ("set_page", "add_page"):
                    count += 1
                    assert inner["output"] == count - 1
                dark = dark or row["tool"] == "apply_theme"
                body = (FOLDER / row["snapshot"]).read_bytes()
                assert sha(body) == row["artifact_sha256"]
                assert not check_document(body.decode(), cases[name][:count], dark)
                if row["tool"] == "load_slidev":
                    assert body == previous
                if row["tool"] == "get_all_slides":
                    assert not check_records(row["result"], cases[name])
                previous = body
    failed = read("render/results.json")
    assert len(failed) == 4 and all(not r["pass"] for r in failed)
    rendered = read("render-v2/results.json")
    assert len(rendered) == 18 and all(not r["pass"] for r in rendered)
    for row in rendered:
        dom = row["dom"]
        assert row["canary"] in dom["text"]
        assert dom["background"] == "rgb(15, 23, 42)"
        assert not dom["overflow"] and dom["scrollHeight"] <= dom["clientHeight"] + 2
        assert set(row["consoleErrors"]) == {"NotAllowedError: Wake Lock permission request denied"}
        assert sha((FOLDER / "render-v2" / row["screenshot"]).read_bytes()) == row["screenshot_sha256"]
    inputs = read("render-v2/inputs.json")
    assert len(inputs) == 4 and all(r["source_sha256"] == r["copy_sha256"] for r in inputs)
    decision = read("admission-decision.json")
    assert decision["preregistered_render_properties_pass"]
    assert decision["collector_all_checks_pass"] is False
    print(json.dumps({"verified": True, "frozen_inputs": len(files), "native_calls": 40,
                      "pages": 18, "retained_failed_render_measurements": 4,
                      "all_checks_flag_still_false": True, "model_calls": 0,
                      "limit": "Deterministic state/render-field verification; visual judgments remain documented human-readable evidence."}))


if __name__ == "__main__":
    main()
