"""One frozen, scored cell. No silent strategy fallback or trajectory retry."""

import argparse
import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv

from pe6203.baselines import write_adaptation
from pe6203.benchmark import read_json, write_json
from pe6203.runner import run


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--arm", required=True)
    parser.add_argument("--task", type=int, required=True)
    parser.add_argument("--stage", required=True)
    parser.add_argument("--endpoint", required=True)
    args = parser.parse_args()
    home, root = args.plan.parent, Path.cwd()
    inputs, plan = home / "inputs", read_json(args.plan)
    load_dotenv("/Users/q/Desktop/tool-selective_patch/V5/.env.v5", override=True)
    for role in ["AGENT", "JUDGE"]:
        os.environ[role + "_BASE_URL"] = args.endpoint
    cell = home / "cells" / args.arm / f"task{args.task}-{args.stage}-r0"
    cell.mkdir(parents=True, exist_ok=False)
    metadata = inputs / "catalogs" / str(args.task)
    updater = read_json(inputs / "local-v5-updater.json")
    config = read_json(inputs / "local-v5-execution.json")
    artifact = None
    started = time.monotonic()
    status = {"arm": args.arm, "task_id": args.task, "stage": args.stage, "status": "started"}
    write_json(cell / "cell.json", status)
    try:
        strategy = args.arm if args.arm in ["no_update", "full_rewrite"] else "selective_patch"
        context = {"updater": {**updater, "allow_metadata_api": True}}
        if args.arm == "V5":
            context.update(selective_mode="hybrid_v5", patch_budget=plan["patch_budget"])
            bundle = inputs / "probes" / str(args.task) / args.stage / "evidence.json"
            if bundle.exists():
                context["evidence_bundle"] = str(bundle)
        elif args.arm == "V3":
            from pe6203.capability import load_evidence

            context.update(
                selective_mode="hybrid_v3",
                patch_budget=plan["patch_budget"],
                capability_evidence=load_evidence(
                    inputs / "v3-evidence" / str(args.task) / args.stage / "evidence.json"
                ),
            )
        artifact = write_adaptation(
            metadata / "early.json",
            metadata / f"{args.stage}.json",
            strategy,
            cell / "adaptation",
            context,
        )
        write_json(cell / "adaptation-timing.json", {"seconds": time.monotonic() - started})
        if args.arm == "V5":
            from pe6203.execution_v5 import run_v5

            if args.task == 133:
                config["task_context"] = (inputs / "python-task-context.txt").read_text()
            write_json(cell / "execution-config.json", config)
            _, result = run_v5(
                root,
                args.task,
                args.stage,
                0,
                cell / "execution-config.json",
                cell / "adaptation/adaptation.json",
                cell / "run",
                inputs / "python-protocol.json" if args.task == 133 else None,
                non_python_deliverable=args.task != 133,
            )
        else:
            config.update(root=str(root), output_dir=str(cell / "run"))
            if args.arm == "V3" and args.task == 133:
                config["task_context"] = (inputs / "python-task-context.txt").read_text()
                config["artifact_validation"] = read_json(inputs / "python-protocol.json")
            config["evaluation_scope"] = "full_system_baselines_unchanged"
            config["attempted_pipeline"] = args.arm
            if artifact["target_stage"] != args.stage:
                # V3's writer labels unchanged target metadata with the retained
                # Early envelope. The documented frozen-knowledge runner permits
                # retained Early knowledge in later environments. Do not rewrite
                # its original artifact or method implementation to hide this.
                assert args.arm == "V3"
                config["knowledge_path"] = str(cell / "adaptation/knowledge.json")
                config["update_cost"] = artifact["cost"]
                write_json(
                    cell / "serialization-workaround.json",
                    {
                        "reason": "V3 writer target_stage follows retained Early envelope on a no-diff snapshot",
                        "execution_entry": "documented runner.run frozen knowledge_path plus original update_cost",
                        "original_artifact_preserved": True,
                        "requested_environment_stage": args.stage,
                    },
                )
            else:
                config["adaptation_path"] = str(cell / "adaptation/adaptation.json")
            write_json(cell / "execution-config.json", config)
            _, result = run(args.task, args.stage, strategy, 0, config)
        status.update(
            status=result["status"],
            execution_status=result["execution_status"],
            judge_status=result["judge_status"],
            TF=result["TF"],
            PE=result["PE"],
        )
    except BaseException as exc:
        status.update(
            status="adaptation_failed" if artifact is None else "cell_error",
            error_type=type(exc).__name__,
        )
        # Error messages may include arbitrary remote text: retain only supported
        # validation errors, never credentials or raw transport exception strings.
        if isinstance(exc, ValueError):
            message = str(exc)
            for key in ["AGENT_API_KEY", "JUDGE_API_KEY"]:
                if os.environ.get(key):
                    message = message.replace(os.environ[key], "<redacted>")
            status["error"] = message[:3000]
    finally:
        status["seconds"] = time.monotonic() - started
        write_json(cell / "cell.json", status)
    print(json.dumps(status, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
