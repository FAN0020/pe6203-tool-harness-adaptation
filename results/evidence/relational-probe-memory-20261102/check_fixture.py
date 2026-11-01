"""Two setup-only reads; excluded from updater and evaluation evidence."""

import asyncio
import json
from copy import deepcopy

from run_generation import HERE, native_sequence, save

from pe6203.experiment import configure_runtime


async def main():
    assert not (HERE / "fixture-readiness.json").exists()
    inputs = json.loads((HERE / "updater-inputs.json").read_text())
    from run_generation import ROOT

    configure_runtime(ROOT)
    records = []
    for original in inputs["jobs"]:
        job = deepcopy(original)
        job["id"] = "setup-" + job["stage"]
        project = inputs["fixture"]["projects"][0]
        steps = {
            "steps": [
                {
                    "id": "P1",
                    "tool": "get_project",
                    "arguments": {"workingDirectory": "$WORKSPACE", "id": project["id"]},
                    "question": "Setup only: frozen fixture readable.",
                }
            ]
        }
        rows = await native_sequence(job, steps, inputs["fixture"], setup=True)
        text = json.dumps(rows[0].get("result", {}))
        passed = (
            project["id"] in text
            and project["name"] in text
            and not rows[0].get("result", {}).get("isError")
        )
        records.append(
            {"stage": job["stage"], "passed": passed, "receipt": f"native/{job['id']}/P1.json"}
        )
    save(
        "fixture-readiness.json",
        {
            "passed": all(r["passed"] for r in records),
            "checks": records,
            "native_calls": 2,
            "catalog_reads": 2,
            "model_calls": 0,
            "updater_evidence": False,
        },
    )
    assert all(r["passed"] for r in records)
    print(
        json.dumps({"fixture_ready": True, "native_calls": 2, "catalog_reads": 2, "model_calls": 0})
    )


if __name__ == "__main__":
    asyncio.run(main())
