"""Run the finite pre-registered native counterfactuals; no model calls."""

import asyncio
import importlib.util
import json
import subprocess
from pathlib import Path
from pe6203.experiment import verify_files, configure_runtime
from pe6203.pruned_episode_memory import select_replay, memory_note
from pe6203.benchmark import write_json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OLD = HERE.parent / "relational-probe-memory-20261102"


async def main():
    freeze = json.loads((HERE / "native-freeze.json").read_text())
    verify_files(ROOT, freeze["files"])
    assert not (HERE / "native-result.json").exists()
    assert not subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT).strip()
    spec = importlib.util.spec_from_file_location("native_runner", OLD / "run_generation.py")
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    runner.HERE = HERE
    inputs = json.loads((OLD / "updater-inputs.json").read_text())
    configure_runtime(ROOT)
    output = []
    feedback = []
    for job in inputs["jobs"]:
        proposal = json.loads((OLD / f"{job['id']}-proposal.json").read_text())
        reference = json.loads((OLD / f"{job['id']}-observations.json").read_text())
        plan = next(j for j in freeze["jobs"] if j["job"] == job["id"])
        trials = []
        for i, steps in enumerate(plan["schedules"]):
            work = dict(job, id=f"{job['id']}-replay{i + 1}")
            reduced = {"steps": [s for s in proposal["steps"] if s["id"] in steps]}
            rows = await runner.native_sequence(work, reduced, inputs["fixture"])
            trials.append({"steps": steps, "rows": rows})
        selected = select_replay(proposal, reference, trials)
        shorter = len(selected["steps"]) < len(proposal["steps"])
        note = memory_note(proposal, reference, trials)
        write_json(HERE / f"{job['id']}-trials.json", trials)
        write_json(HERE / f"{job['id']}-candidate.json", {"note": note})
        output.append(
            {
                "job": job["id"],
                "selected_steps": selected["steps"],
                "shorter": shorter,
                "scheduled_native_calls": plan["native_calls"],
                "note_chars": len(note),
            }
        )
        feedback.append(
            {
                "stage": job["stage"],
                "server": job["data"]["server"],
                "result": {
                    "kind": "pruned_episode_memory_v1",
                    "semantic_review": "pending",
                    "inventory": job["data"],
                    "proposal": proposal,
                    "reference": reference,
                    "trials": trials,
                },
            }
        )
        print(json.dumps(output[-1]), flush=True)
    write_json(
        HERE / "native-result.json",
        {
            "jobs": output,
            "passed": all(j["shorter"] for j in output),
            "native_calls": sum(j["scheduled_native_calls"] for j in output),
            "catalog_reads": 6,
            "model_calls": 0,
            "usd": 0,
        },
    )
    write_json(HERE / "pending-feedback.json", {"observations": feedback})
    verify_files(ROOT, freeze["files"])


if __name__ == "__main__":
    asyncio.run(main())
