"""Offline admission test, not an agent run or a benchmark score.

Reads only two frozen native outputs and a response-metadata projection.
Does not import downloaded research code, load credentials or make requests.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    freeze = read(OUT / "admission-freeze.json")
    for path, expected in freeze["files"].items():
        assert sha(ROOT / path) == expected, path
    protocol = read(ROOT / "experiments/verified-component-memory-admission-v1.json")
    workspace = OUT / "admission-workspace"
    workspace.mkdir(exist_ok=True)
    home = workspace / "home"
    home.mkdir(exist_ok=True)
    fixture = ROOT / "experiments/extensions/magicui-log-dashboard-v1/datasets/development/input"
    shutil.copytree(fixture, workspace / "input", dirs_exist_ok=True)
    node = ROOT / ".cache/node-runtime/node_modules/node/bin/node"
    assert node.is_file()
    env = {"PATH": str(node.parent), "HOME": str(home), "TMPDIR": str(workspace)}
    inventory, selections = [], []
    for source in protocol["sources"]:
        native = read(ROOT / source["path"])
        assert native["result"]["isError"] is False
        entries = []
        for block in native["result"]["content"]:
            if block["type"] == "text":
                entries.extend(json.loads(block["text"]))
        assert entries and all(isinstance(x.get("content"), str) and x["content"] for x in entries)
        inventory.extend({"category": source["category"], "name": x["name"],
                          "code_bytes": len(x["content"].encode())} for x in entries)
        selected = min(entries, key=lambda x: (len(x["content"].encode()), x["name"]))
        code = selected["content"]
        # Imports, including multiline declarations, are preserved in selected.tsx.
        imports = sorted(set(re.findall(r'''\bfrom\s+["']([^"']+)["']''', code)))
        directory = OUT / "selected-programs" / source["category"]
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "selected.tsx").write_text(code)
        (directory / "native-record.json").write_text(json.dumps(selected, indent=2) + "\n")
        parse = subprocess.run([str(node), "--input-type=module", "--check"], input=code,
                               text=True, capture_output=True, cwd=workspace, env=env, timeout=30)
        (directory / "node-check.stdout.txt").write_text(parse.stdout)
        (directory / "node-check.stderr.txt").write_text(parse.stderr)
        probe = "const names=JSON.parse(process.argv[1]);console.log(JSON.stringify(names.map(name=>{try{return {name,resolved:require.resolve(name)}}catch(e){return {name,error:e.code}}})))"
        result = subprocess.run([str(node), "-e", probe, json.dumps(imports)],
                                text=True, capture_output=True, cwd=workspace, env=env, timeout=30)
        assert result.returncode == 0, result.stderr
        resolutions = json.loads(result.stdout)
        all_resolved = all("resolved" in x for x in resolutions)
        # This gate deliberately does not equate parsing/imports with browser correctness.
        selections.append({"category": source["category"], "name": selected["name"],
                           "source": source["path"], "source_sha256": sha(ROOT / source["path"]),
                           "code_sha256": sha(directory / "selected.tsx"),
                           "code_bytes": len(code.encode()), "imports": resolutions,
                           "native_declared_other_fields": {k: v for k, v in selected.items() if k not in ("content", "description", "name")},
                           "node_parse_exit_code": parse.returncode,
                           "dependency_resolution_pass": all_resolved,
                           "rendered_effect": "not_verified",
                           "admitted": False,
                           "reason": "existing_runtime_not_executable" if parse.returncode or not all_resolved else "rendering_still_required"})
    assert len(selections) == 2
    projection = read(ROOT / "results/evidence/extensions/magicui-log-dashboard-v1/mechanism-projection.json")
    bounds = []
    for cell in projection:
        first, last = [cell["responses"][i]["usage"]["prompt_tokens"] for i in (0, -1)]
        bounds.append({"cell": cell["cell"], "first_prompt_tokens": first,
                       "last_prompt_tokens": last,
                       "gross_static_share_percent": 100 * first / last,
                       "noninitial_prompt_growth_tokens": last - first})
    result = {"kind": "offline_candidate_admission_not_model_development", "pre_registration_commit": "386649a",
              "frozen_files_verified": len(freeze["files"]), "source_inventory": inventory,
              "selections": selections, "selected_code_bytes": sum(x["code_bytes"] for x in selections),
              "byte_bound_pass": sum(x["code_bytes"] for x in selections) <= protocol["memory_budget"]["total_native_code_bytes_max"],
              "status": "not_ready_for_agent_trial", "rendered_effects_verified": 0,
              "model_calls": 0, "native_mcp_calls": 0, "usd": 0,
              "TF": None, "PE": None, "ECS": None, "agent_completion": None,
              "context_bounds": bounds,
              "limits": ["First prompt includes user/system/framing as well as tool knowledge; this is a deliberately generous accounting envelope, not exact token re-encoding.",
                         "Holding the observed trajectory fixed excludes any action-selection or output-length effect of changed knowledge.",
                         "No inference that large prompts caused the length stop; no inference that all memory methods fail.",
                         "This is a direct pinned-Node consumption test, not an inventory of every installed compiler or a test of native run-code TypeScript mode; those alternative build paths remain unverified.",
                         "Missing build/runtime dependencies do not prove an agent cannot implement an alternative under the original task. They refute calling these two verbatim programs already verified executable skills.",
                         "A new common runtime or code transformation would require a separate declared environment and revalidation; it cannot be backfilled into this admission result."],
              "goal_complete": False}
    (OUT / "admission-result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: result[k] for k in ("status", "selected_code_bytes", "byte_bound_pass", "model_calls", "usd", "context_bounds")}, indent=2))
    for row in selections:
        print(row["category"], row["name"], row["code_bytes"], row["imports"], row["reason"])


if __name__ == "__main__":
    main()
