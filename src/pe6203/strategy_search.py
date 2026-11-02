"""Prospective patch comparisons with frozen updates and independent confirmation."""

import argparse
import itertools
import json
import random
import statistics
from pathlib import Path

from .baselines import write_adaptation
from .benchmark import read_json, write_json
from .experiment import (
    adaptation_path,
    check_plan,
    freeze_files,
    make_cells,
    prepare,
    run_experiment,
    sha,
    summarize,
    verify_files,
    writer_lock,
)
from .judge import ecs
from .patch_variants import VARIANTS


def cells_for(spec, phase, candidate=None):
    group = spec[phase]
    strategies = [candidate if s == "selected_candidate" else s for s in group["strategies"]]
    if phase == "confirmation" and candidate not in VARIANTS:
        raise ValueError("Choose a registered candidate for fresh confirmation")
    cells = make_cells(group["tasks"], group["stages"], strategies, group["repeats"])
    if "task_stage_pairs" in group:
        pairs = [tuple(pair) for pair in group["task_stage_pairs"]]
        allowed = {(c["task_id"], c["version"]) for c in cells}
        if not pairs or len(pairs) != len(set(pairs)) or not set(pairs) <= allowed:
            raise ValueError("Need distinct supported task-stage pairs")
        cells = [c for c in cells if (c["task_id"], c["version"]) in pairs]
    if "execution_cells" in group:
        requested = [tuple(row) for row in group["execution_cells"]]
        fields = ("task_id", "version", "strategy", "seed")
        available = {tuple(c[k] for k in fields) for c in cells}
        if (
            not requested
            or len(requested) != len(set(requested))
            or not set(requested) <= available
        ):
            raise ValueError("Need distinct supported execution cells")
        cells = [c for c in cells if tuple(c[k] for k in fields) in requested]
    # Complete repeat blocks, randomized within each block; no model seed promise.
    random.Random(1729).shuffle(cells)
    cells = sorted(cells, key=lambda c: c["seed"])
    if group.get("opaque_cell_ids"):
        for index, cell in enumerate(cells, 1):
            cell["id"] = f"cell-{index:03d}"
    return cells


def prepare_search(root, output, spec_path, phase, candidate=None, round_number=1):
    root, output = Path(root).resolve(), Path(output).resolve()
    spec = read_json(root / spec_path)
    cells = cells_for(spec, phase, candidate)
    group = spec[phase]
    if any(c["strategy"] == "budget_contract" for c in cells):
        config = read_json(root / spec["model_config"])
        if config.get("max_rounds") != 12 or config["agent"].get("max_completion_tokens") != 4096:
            raise ValueError("budget_contract requires 12 rounds and 4096 output tokens")
    plan = prepare(
        root,
        output,
        group["tasks"],
        group["stages"],
        sorted({c["strategy"] for c in cells}),
        group["repeats"],
        spec["model_config"],
        spec["updater_config"],
    )
    plan.update(
        kind="research_" + phase,
        formal_evaluation=False,
        cells=cells,
        research={
            "spec": spec,
            "phase": phase,
            "candidate": candidate,
            "confirmation_round": round_number,
        },
        availability_preflight=True,
        stop_after_infrastructure_failures=2,
    )
    if "preflight_calls_max" in spec.get("authorization", {}):
        plan["max_preflight_calls"] = spec["authorization"]["preflight_calls_max"]
    print(f"Explicit research schedule frozen: {len(cells)} trajectories.", flush=True)
    plan["shared_adaptations"] = {
        f"{c['task_id']}-{c['version']}-{c['strategy']}": f"adaptations/{c['task_id']}-{c['version']}-{c['strategy']}/adaptation.json"
        for c in cells
    }
    feedback_path = root / spec.get("feedback_probes", "experiments/feedback-probes-v1.json")
    write_json(output / "feedback.json", read_json(feedback_path))
    plan["files"].update(
        freeze_files(
            root,
            [
                root / spec_path,
                root / spec["model_config"],
                root / spec["updater_config"],
                feedback_path,
                output / "feedback.json",
            ],
        )
    )
    write_json(output / "plan.json", plan)
    (output / "plan.sha256").write_text(sha(output / "plan.json") + "\n")
    print("下一步 search build：每个任务/阶段/策略生成一次知识，随后审查并冻结。", flush=True)
    return plan


def build(root, output):
    output = Path(output).resolve()
    with writer_lock(output):
        plan = read_json(output / "plan.json")
        check_plan(root, output, plan)
        if (output / "knowledge-lock.json").exists():
            verify_files(output, read_json(output / "knowledge-lock.json")["files"])
            print("知识已冻结；不重新生成。")
            return
        if (output / "experiment.json").exists():
            raise ValueError("Cannot build updates after execution started")
        observations = read_json(output / "feedback.json")["observations"]
        seen = set()
        for cell in plan["cells"]:
            artifact = adaptation_path(output, plan, cell)
            if artifact in seen:
                continue
            seen.add(artifact)
            if artifact.exists():
                if read_json(artifact)["status"] != "validated":
                    raise ValueError(
                        "Failed update is retained; create a new version, do not replace it"
                    )
                continue
            print("生成并保存 " + artifact.parent.name, flush=True)
            context = {"updater": {**plan["updater"], "allow_metadata_api": True}}
            if cell["strategy"] in VARIANTS:
                context["feedback"] = observations
            write_adaptation(
                output / "catalogs" / str(cell["task_id"]) / "early.json",
                output / "catalogs" / str(cell["task_id"]) / f"{cell['version']}.json",
                cell["strategy"],
                artifact.parent,
                context,
            )
        write_json(
            output / "knowledge-lock.json",
            {
                "plan_sha256": sha(output / "plan.json"),
                "files": freeze_files(output, list((output / "adaptations").rglob("*.json"))),
            },
        )
        print(
            "全部知识已冻结；审查 updater-audit.json 的语义依据后运行 search review。", flush=True
        )


def check_knowledge(output):
    output = Path(output)
    if not (output / "knowledge-lock.json").exists():
        raise ValueError("Build and review frozen knowledge first")
    lock = read_json(output / "knowledge-lock.json")
    verify_files(output, lock["files"])
    if lock.get("plan_sha256") and lock["plan_sha256"] != sha(output / "plan.json"):
        raise ValueError("Frozen knowledge plan changed")
    review = output / "knowledge-review.json"
    if not review.exists():
        raise ValueError("Semantic knowledge review is required before execution")
    review = read_json(review)
    if not review.get("accepted") or review.get("lock_sha256") != sha(
        output / "knowledge-lock.json"
    ):
        raise ValueError("Knowledge review must accept this exact frozen knowledge")


def review(output, note):
    output = Path(output)
    verify_files(output, read_json(output / "knowledge-lock.json")["files"])
    for artifact in (output / "adaptations").glob("*/adaptation.json"):
        if read_json(artifact)["status"] != "validated":
            raise ValueError("Cannot accept failed adaptation")
    if (output / "knowledge-review.json").exists():
        raise ValueError("Review already recorded; never overwrite")
    write_json(
        output / "knowledge-review.json",
        {"accepted": True, "lock_sha256": sha(output / "knowledge-lock.json"), "note": note},
    )
    check_knowledge(output)


def mean(values):
    values = list(values)
    return statistics.mean(values) if values and all(v is not None for v in values) else None


def sign_flip(differences):
    """Exact paired randomization; unit is an execution pair, never a judge rating."""
    differences = [d for d in differences if d != 0]
    if not differences:
        return 1.0
    observed = sum(differences)
    return sum(
        sum(s * d for s, d in zip(signs, differences, strict=True)) >= observed - 1e-9
        for signs in itertools.product((-1, 1), repeat=len(differences))
    ) / 2 ** len(differences)


def promotion(rows, candidate, spec, round_number):
    decision = {
        "promote": False,
        "candidate": candidate,
        "alpha": 0.05 / 2**round_number,
        "scope": "Fresh repeat executions on this fixed, already exposed task set only",
    }
    expected = set(
        itertools.product(
            [133, 235, 283],
            ["early", "middle", "late"],
            range(3),
            ["no_update", "full_rewrite", "selective_patch", candidate],
        )
    )
    keys = [(r["task_id"], r["version"], r["seed"], r["strategy"]) for r in rows]
    if (
        len(keys) != len(expected)
        or set(keys) != expected
        or any(r.get("TF") is None or r.get("PE") is None for r in rows)
    ):
        return {**decision, "reason": "All 108 executions and 540 valid ratings are required"}
    champion = "selective_patch"
    indexed = dict(zip(keys, rows, strict=True))
    differences = [
        indexed[t, v, r, candidate]["PE"] - indexed[t, v, r, champion]["PE"]
        for t, v, r in itertools.product([133, 235, 283], ["middle", "late"], range(3))
    ]
    gate = spec["promotion_gate"]
    groups = {arm: [r for r in rows if r["strategy"] == arm] for arm in [champion, candidate]}
    tf_delta = mean(r["TF"] for r in groups[candidate]) - mean(r["TF"] for r in groups[champion])

    def ecs_mean(arm):
        return mean(
            ecs({v: indexed[t, v, rep, arm]["TF"] for v in ["early", "middle", "late"]})[
                "upstream_population"
            ]
            for t, rep in itertools.product([133, 235, 283], range(3))
        )

    ecs_delta = ecs_mean(candidate) - ecs_mean(champion)
    worst_tf = min(
        mean(
            indexed[t, v, rep, candidate]["TF"] - indexed[t, v, rep, champion]["TF"]
            for rep in range(3)
        )
        for t, v in itertools.product([133, 235, 283], ["early", "middle", "late"])
    )
    repeat_deltas = [
        mean(
            indexed[t, v, rep, candidate]["PE"] - indexed[t, v, rep, champion]["PE"]
            for t, v in itertools.product([133, 235, 283], ["middle", "late"])
        )
        for rep in range(3)
    ]
    completed = {
        arm: sum(r["execution_status"] == "completed" for r in group)
        for arm, group in groups.items()
    }
    p = sign_flip(differences)
    gates = {
        "PE_gain": mean(differences) >= gate["delta_PE_vs_champion_min"] - 1e-9,
        "TF_noninferiority": tf_delta >= -gate["TF_mean_noninferiority_margin"] - 1e-9,
        "ECS_noninferiority": ecs_delta >= -gate["ECS_noninferiority_margin"] - 1e-9,
        "per_task_stage_TF": worst_tf >= -gate["max_task_stage_TF_regression"] - 1e-9,
        "completed_executions": completed[candidate] >= completed[champion],
        "repeat_consistency": sum(d > 0 for d in repeat_deltas) >= 2,
        "paired_sign_flip": p <= decision["alpha"],
    }
    return {
        **decision,
        "promote": all(gates.values()),
        "gates": gates,
        "post_change_pairs": len(differences),
        "delta_PE": mean(differences),
        "delta_TF": tf_delta,
        "delta_ECS": ecs_delta,
        "worst_task_stage_TF_delta": worst_tf,
        "repeat_PE_deltas": repeat_deltas,
        "paired_differences": differences,
        "p_one_sided": p,
        "completed": completed,
    }


def report(output):
    output = Path(output)
    plan = read_json(output / "plan.json")
    summary = summarize(output)
    arms = {}
    for arm in sorted({r["strategy"] for r in summary["rows"]}):
        rows = [r for r in summary["rows"] if r["strategy"] == arm]
        scored = [r for r in rows if r["TF"] is not None]
        arms[arm] = {
            "scored": len(scored),
            "planned": len(rows),
            "TF": mean(r["TF"] for r in scored),
            "PE": mean(r["PE"] for r in scored),
            "post_change_PE": mean(r["PE"] for r in scored if r["version"] != "early"),
            "completed_execution": sum(r["execution_status"] == "completed" for r in rows),
            "ECS": mean(r["upstream_population"] for r in summary["ecs"] if r["strategy"] == arm),
        }
    study = {
        "phase": plan["research"]["phase"],
        "observed_partial_means_until_all_cells_scored": True,
        "arms": arms,
        "planned": summary["planned"],
        "scored": summary["scored"],
        "cost": summary["cost"],
        "decision": None,
    }
    if plan["research"]["phase"] == "confirmation":
        study["decision"] = promotion(
            summary["rows"],
            plan["research"]["candidate"],
            plan["research"]["spec"],
            plan["research"]["confirmation_round"],
        )
    write_json(output / "search-summary.json", study)
    print(json.dumps(study, ensure_ascii=False, indent=2))
    return study


def main(root, arguments):
    parser = argparse.ArgumentParser(
        prog="./experiment search",
        description="文献补丁研究；固定知识、保留所有结果，独立确认后才晋级",
    )
    sub = parser.add_subparsers(dest="action", required=True)
    p = sub.add_parser("prepare", help="读取工具目录并固定计划，不调用模型")
    p.add_argument("--spec", type=Path, default=Path("experiments/selective-search-v3.json"))
    p.add_argument("--phase", choices=["development", "confirmation"], default="development")
    p.add_argument("--candidate", choices=VARIANTS)
    p.add_argument("--round", type=int, default=1)
    p.add_argument("--output", type=Path, required=True)
    for action in ["build", "review", "run", "report"]:
        p = sub.add_parser(action)
        p.add_argument("--output", type=Path, required=True)
        if action == "review":
            p.add_argument("--note", required=True, help="记录已完成的语义依据审查")
        if action == "run":
            p.add_argument("--limit", type=int)
    args = parser.parse_args(arguments)
    try:
        if args.action == "prepare":
            if args.round < 1:
                raise ValueError("Round must be positive")
            prepare_search(root, args.output, args.spec, args.phase, args.candidate, args.round)
        elif args.action == "build":
            build(root, args.output)
        elif args.action == "review":
            review(args.output, args.note)
        elif args.action == "run":
            if args.limit is not None and args.limit < 1:
                raise ValueError("Limit must be positive")
            run_experiment(root, args.output, resume=True, limit=args.limit)
            study = report(args.output)
            return 0 if study["scored"] == study["planned"] else 2
        else:
            report(args.output)
    except Exception as exc:
        print(str(exc) if isinstance(exc, (ValueError, OSError)) else type(exc).__name__)
        return 2
    return 0
