"""Synthetic parser tests only. These are not benchmark trajectories."""

import copy
import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "v2_eval", Path(__file__).resolve().parents[1] / "scripts/evaluate_v2.py"
)
ev = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ev)


class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        cells = [
            {"id": f"task{t}-{v}-{s}-r0", "task_id": t, "version": v, "strategy": s, "seed": 0}
            for t in (133, 235, 283)
            for v in ("early", "middle", "late")
            for s in ("no_update", "full_rewrite", "selective_patch")
        ]
        self.plan = {
            "cells": cells,
            "config": {"test": "synthetic"},
            "tasks": [{"idx": t, "question": f"Synthetic question {t}"} for t in (133, 235, 283)],
            "suite": {
                "suite_id": "course-qi-v2-eval-20261101",
                "tasks": [
                    {
                        "task_id": t,
                        "question_sha256": hashlib.sha256(
                            f"Synthetic question {t}".encode()
                        ).hexdigest(),
                    }
                    for t in (133, 235, 283)
                ],
            },
        }
        self.save_plan()

    def save_plan(self):
        ev.write(self.root / "plan.json", self.plan)
        (self.root / "plan.sha256").write_text(ev.sha(self.root / "plan.json"))

    def cell(self, state="output_truncated", score=10):
        c = self.plan["cells"][0]
        d = self.root / "cells" / c["id"]
        ev.write(
            d / "run/result.json",
            {
                "config": self.plan["config"],
                "status": "evaluated",
                "execution_status": state,
                "judge_status": "complete",
                "cost": {},
            },
        )
        ratings = {"task_fulfillment": score, "planning_and_efficiency": score, "grounding": score}
        ev.write(
            d / "run/EVAL/133.json",
            {
                "eval_result": {
                    "runs": [{"result": ratings} for _ in range(5)],
                    "aggregate": {
                        "successful_runs": 5,
                        "total_runs": 5,
                        **{k + "_mean": score for k in ratings},
                    },
                }
            },
        )
        ev.write(
            d / "run/raw_trace.json",
            {
                "answer": "Synthetic answer",
                "trajectory_messages": [{"role": "user", "content": "Synthetic question 133"}],
            },
        )
        return d

    def test_pending_not_zero_scores_or_cost(self):
        s = ev.summarize(self.root)
        self.assertEqual(s["scored_executions"], 0)
        self.assertIsNone(s["strategies"][0]["TF_mean_available"])
        self.assertIsNone(s["strategies"][0]["cost"]["update"]["usd"])

    def test_high_score_truncation_is_not_completion(self):
        self.cell()
        s = ev.summarize(self.root)
        self.assertEqual(s["scored_executions"], 1)
        self.assertEqual(s["strategies"][0]["normally_completed"], 0)
        self.assertEqual(s["matched_three_method_cells"], 0)

    def test_completion_denominator_includes_pending(self):
        self.cell("completed")
        s = ev.summarize(self.root)
        self.assertEqual(s["strategies"][0]["completion_rate_planned"], 1 / 9)

    def test_four_ratings_not_complete(self):
        d = self.cell()
        p = d / "run/EVAL/133.json"
        data = ev.read(p)
        data["eval_result"]["runs"].pop()
        ev.write(p, data)
        self.assertEqual(ev.summarize(self.root)["scored_executions"], 0)

    def test_reject_old_patch(self):
        c = self.plan["cells"][2]
        ev.write(
            self.root / "cells" / c["id"] / "adaptation/adaptation.json",
            {"status": "validated", "pipeline_version": "deterministic_v1"},
        )
        with self.assertRaisesRegex(ValueError, "Non-V2"):
            ev.summarize(self.root)

    def test_reject_changed_question(self):
        d = self.cell()
        p = d / "run/raw_trace.json"
        data = ev.read(p)
        data["trajectory_messages"][0]["content"] = "different question"
        ev.write(p, data)
        with self.assertRaisesRegex(ValueError, "task mismatch"):
            ev.summarize(self.root)

    def test_reject_changed_settings(self):
        d = self.cell()
        p = d / "run/result.json"
        data = ev.read(p)
        data["config"] = {}
        ev.write(p, data)
        with self.assertRaisesRegex(ValueError, "settings differ"):
            ev.summarize(self.root)

    def test_cost_partial_known_and_unknown(self):
        c = ev.costs([{"usd": 0.2}, {"usd": None, "known_usd": 0.1}])
        self.assertAlmostEqual(c["known_usd"], 0.3)
        self.assertIsNone(c["usd"])
        self.assertEqual(c["unknown_usd_records"], 1)

    def test_reject_duplicate_cells(self):
        self.plan["cells"][0] = copy.deepcopy(self.plan["cells"][1])
        self.save_plan()
        with self.assertRaisesRegex(ValueError, "27 distinct"):
            ev.summarize(self.root)

    def test_answer_and_workspace_are_preserved(self):
        d = self.cell("completed")
        (d / "run/workspace").mkdir()
        (d / "run/workspace/product.txt").write_text("synthetic product")
        ev.summarize(self.root)
        p = self.root / "v2-eval/cases" / (self.plan["cells"][0]["id"] + ".json")
        case = ev.read(p)
        self.assertEqual(case["final_answer"], "Synthetic answer")
        self.assertEqual(len(case["workspace_manifest"]), 1)
        self.assertEqual(case["artifact_quality"], "not_manually_reviewed")


if __name__ == "__main__":
    unittest.main()
