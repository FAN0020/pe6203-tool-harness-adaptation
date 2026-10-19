"""Real initialization/catalog probes. These do not execute a model or score tasks."""

import asyncio
import hashlib
import time
from pathlib import Path

from .benchmark import digest, source, write_json
from .transport import server_profiles, sessions, snapshot


def error_detail(exc):
    if isinstance(exc, BaseExceptionGroup):
        return "; ".join(error_detail(child) for child in exc.exceptions)
    return f"{type(exc).__name__}: {exc}"


async def probe_servers(root, stages, output, timeout=30):
    lock, _ = source(root)
    profiles = server_profiles(root, lock)
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    report = {
        "kind": "real_mcp_catalog_probe",
        "benchmark_commit": lock["commit"],
        "dataset_revision": lock["dataset_revision"],
        "model_used": None,
        "task_evaluation": False,
        "servers": [],
    }
    for stage in stages:
        for server in sorted(profiles):
            key = hashlib.sha256(server.encode()).hexdigest()[:12]
            directory = output / stage / key
            directory.mkdir(parents=True)
            started = time.monotonic()
            record = {"server_id": server, "version": stage, "status": "failed"}
            try:
                async with asyncio.timeout(timeout):
                    async with sessions(
                        root,
                        stage,
                        [server],
                        directory / "workspace",
                        directory / "stderr.log",
                        timeout,
                    ) as clients:
                        metadata = await snapshot(clients, stage, lock["commit"])
                write_json(directory / "metadata.json", metadata)
                record.update(
                    {
                        "status": "catalog_verified",
                        "tool_count": len(metadata["tools"]),
                        "metadata_path": str((directory / "metadata.json").relative_to(output)),
                        "metadata_object_sha256": digest(metadata),
                    }
                )
            except Exception as exc:
                record["error"] = error_detail(exc)
            record["seconds"] = round(time.monotonic() - started, 6)
            report["servers"].append(record)
            write_json(output / "server-probes.json", report)
    return report
