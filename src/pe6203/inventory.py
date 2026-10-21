"""Read-only census of selected tasks, launch configurations and released archives.

Archive availability is not evidence that a service starts or a task succeeds.
Reference answers, trajectories and credential values never enter this report.
"""

import hashlib
import json
from collections import Counter
from pathlib import Path, PurePosixPath
from zipfile import ZipFile

from .benchmark import load_task, read_json


def archive_entry(config, archive):
    if config is None:
        return {"status": "missing_config"}
    command = config.get("command")
    result = {"command_type": command, "env_names": sorted(config.get("env", {}))}
    if command not in ("node", "npx"):
        return {**result, "status": "not_in_node_archive"}
    if archive is None:
        return {**result, "status": "missing_archive"}
    names = archive.NameToInfo
    args = config.get("args", [])
    if command == "node":
        if not args or "/node_modules/" not in args[0]:
            return {**result, "status": "unresolved_entry"}
        entry = "node_modules/" + args[0].split("/node_modules/", 1)[1]
        parts = PurePosixPath(entry).parts
        package = "/".join(parts[1:3] if parts[1].startswith("@") else parts[1:2])
        extra = args[1:]
    else:
        positional = [a for a in args if a not in ("-y", "--yes")]
        if not positional or positional[0].startswith("-"):
            return {**result, "status": "unresolved_entry"}
        package, extra = positional[0], positional[1:]
        entry = None
    metadata_path = f"node_modules/{package}/package.json"
    if metadata_path not in names:
        return {**result, "status": "missing_package", "package": package}
    metadata = json.loads(archive.read(metadata_path))
    if entry is None:
        bins = metadata.get("bin", {})
        if isinstance(bins, str):
            binary = bins
        elif package.rsplit("/", 1)[-1] in bins:
            binary = bins[package.rsplit("/", 1)[-1]]
        elif len(bins) == 1:
            binary = next(iter(bins.values()))
        else:
            return {**result, "status": "ambiguous_bin", "package": package}
        entry = f"node_modules/{package}/{binary}"
    entry = str(PurePosixPath(entry))
    return {
        **result,
        "status": "entry_available" if entry in names else "missing_entry",
        "package": package,
        "package_version": metadata.get("version"),
        "entry": entry,
        "extra_argument_count": len(extra),
        # Values may include passwords, host paths or external service URLs.
        "runtime_arguments_require_review": bool(extra),
    }


def build_inventory(upstream, lock, cache):
    upstream, cache = Path(upstream), Path(cache)
    data = upstream / "src/custom/data/test_cases"
    ids = sorted(x["idx"] for x in read_json(data / "chosen_idx.json")["samples"])
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate selected task IDs")
    tasks = [load_task(upstream, task_id) for task_id in ids]
    configs = {
        stage: read_json(upstream / f"servers/1mcp_config/{spec['directory']}/mcp.json")[
            "mcpServers"
        ]
        for stage, spec in lock["stages"].items()
    }
    used = Counter(server for task in tasks for server in task["servers"])
    server_ids = sorted(set(used).union(*(set(c) for c in configs.values())))
    statuses_path = data / "status_dict.json"
    statuses = read_json(statuses_path) if statuses_path.exists() else {}
    servers = {
        sid: {
            "server_id": sid,
            "selected_task_ids": [t["idx"] for t in tasks if sid in t["servers"]],
            "published_tool_count": len(statuses[sid].get("tools", []))
            if sid in statuses
            else None,
            "runtime_verified": False,
            "stages": {},
        }
        for sid in server_ids
    }
    for stage, spec in lock["stages"].items():
        path = cache / spec["archive"]
        archive = ZipFile(path) if path.exists() else None
        try:
            for sid in server_ids:
                servers[sid]["stages"][stage] = archive_entry(configs[stage].get(sid), archive)
        finally:
            if archive:
                archive.close()
    records = []
    for task in tasks:
        records.append(
            {
                "task_id": task["idx"],
                "question": task["question"],
                "question_sha256": hashlib.sha256(task["question"].encode()).hexdigest(),
                "servers": task["servers"],
                "runtime_verified": False,
                "fixture_review": "not_reviewed",
                "stage_blockers": {
                    stage: [
                        {"server_id": sid, "reason": servers[sid]["stages"][stage]["status"]}
                        for sid in task["servers"]
                        if servers[sid]["stages"][stage]["status"] != "entry_available"
                    ]
                    for stage in configs
                },
            }
        )
    return {
        "schema_version": "1.0",
        "kind": "static_release_inventory_not_runtime_evaluation",
        "benchmark_commit": lock["commit"],
        "dataset_revision": lock["dataset_revision"],
        "summary": {
            "selected_tasks": len(tasks),
            "task_server_names": len(used),
            "configured_server_names": {s: len(c) for s, c in configs.items()},
            "union_server_names": len(server_ids),
            "published_status_servers": len(statuses),
            "published_status_tools": sum(len(v.get("tools", [])) for v in statuses.values()),
            "missing_config_task_servers": {
                stage: sorted(set(used) - set(c)) for stage, c in configs.items()
            },
            "stage_task_archive_ready": {
                stage: sum(not t["stage_blockers"][stage] for t in records) for stage in configs
            },
            "stage_server_status_counts": {
                stage: dict(Counter(s["stages"][stage]["status"] for s in servers.values()))
                for stage in configs
            },
        },
        "tasks": records,
        "servers": list(servers.values()),
    }
