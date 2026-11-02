"""Offline verification of native filtering defect and successful glyph alternative."""
import hashlib
import json
import tarfile
from pathlib import Path

FOLDER = Path(__file__).resolve().parent
PREFIX = "results/evidence/icon-style-filter-probes-20261101/"


def sha(value):
    return hashlib.sha256(value).hexdigest()


def main():
    manifest = json.loads((FOLDER / "archive-manifest.json").read_text())
    archive = FOLDER / "probe-and-source.tar.gz"
    assert sha(archive.read_bytes()) == manifest["archive_sha256"]
    with tarfile.open(archive) as tar:
        files = {m.name: tar.extractfile(m).read() for m in tar if m.isfile()}
    assert {k: sha(v) for k, v in files.items()} == manifest["files"]
    plan_path = "experiments/icon-style-filter-probes-v1.json"
    plan = json.loads(files[plan_path])
    pre = json.loads(files[PREFIX + "preexecution.json"])
    assert pre["plan_sha256"] == sha(files[plan_path])
    assert pre["collector_sha256"] == sha(files[PREFIX + "run_probes.py"])
    for item in plan["source"]:
        assert sha(files[item["path"]]) == item["sha256"]
    execution = json.loads(files[PREFIX + "execution.json"])
    assert execution["status"] == "completed_requires_review"
    assert execution["tool_calls"] == 8 and execution["catalog_calls"] == 3
    assert execution["model_calls"] == execution["model_usd"] == 0
    rows = json.loads(files[PREFIX + "observations.json"])
    assert len(rows) == 8
    defaults, glyphs = [], []
    for stage in plan["stages"]:
        stage_rows = [r for r in rows if r["stage"] == stage]
        assert [r["kind"] for r in stage_rows] == plan["schedule"][stage]
        decoded = {}
        for r in stage_rows:
            assert r == json.loads(files[PREFIX + f"{stage}-{r['index']:02d}.json"])
            assert "exception" not in r and not r["result"].get("isError")
            decoded[r["kind"]] = json.loads("\n".join(
                c.get("text", "") for c in r["result"]["content"]))
        found = decoded["search_default"]
        assert len(found) == 66
        assert all(not {"style", "variant", "stroke"}.intersection(x) for x in found)
        defaults.append(found)
        if stage != "early":
            assert decoded["search_style"] == []
        glyph = decoded["glyph_by_style"]
        assert glyph["primary"]["icon_name"] == found[0]["name"]
        assert glyph["primary"]["style"] == plan["style"]
        assert glyph["primary"]["unicode_decimal"] == 995429
        glyphs.append(glyph)
    assert defaults[0] == defaults[1] == defaults[2]
    assert glyphs[0] == glyphs[1] == glyphs[2]
    print(json.dumps({"archive_integrity": True, "files": len(files),
                      "tool_calls": 8, "catalog_calls": 3, "model_calls": 0,
                      "default_count_each": 66, "default_sets_identical": True,
                      "style_false_empty_middle_late": True,
                      "native_glyph_alternative": True,
                      "agent_improvement_tested": False, "goal_complete": False}, indent=2))


if __name__ == "__main__":
    main()
