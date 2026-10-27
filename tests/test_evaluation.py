import copy
import json
import tempfile
import unittest
from pathlib import Path

from pe6203 import evaluation as ev


def judge(tf=8, pe=7):
    rows = [
        {"result": {"task_fulfillment": tf, "planning_and_efficiency": pe, "grounding": 9}}
        for _ in range(5)
    ]
    return {
        "idx": 105,
        "eval_result": {
            "runs": rows,
            "aggregate": {
                "successful_runs": 5,
                "total_runs": 5,
                "task_fulfillment_mean": tf,
                "planning_and_efficiency_mean": pe,
                "grounding_mean": 9,
            },
        },
    }


def data():
    m = {
        "experiment_id": "synthetic-test-only",
        "evidence_kind": "synthetic_software_test",
        "frozen": False,
        "comparison_config_file_sha256": "test-only",
        "repeat_ids": [0],
        "tasks": [
            {
                "task_id": 105,
                "transitions": {
                    v: {"label": "changed", "change_types": ["PARAM"]} for v in ev.STAGES[1:]
                },
            }
        ],
    }
    selected = {}
    for v in ev.STAGES:
        for s in ev.STRATEGIES:
            selected[105, v, s, 0] = {
                "task_id": 105,
                "stage": v,
                "strategy": s,
                "repeat_id": 0,
                "TF": 6 if s == "no_update" else 8,
                "PE": 7,
                "eligible": True,
                "reason": None,
            }
    return m, selected


class EvaluationTests(unittest.TestCase):
    def test_ecs_reference(self):
        self.assertAlmostEqual(ev.ecs([6, 8, 10]), 6.367006838144548)
        self.assertAlmostEqual(ev.ecs([6, 8, 10], True), 6)

    def test_ecs_constant(self):
        self.assertEqual(ev.ecs([7, 7, 7]), 7)

    def test_ecs_missing(self):
        with self.assertRaises(ValueError):
            ev.ecs([6, None, 8])

    def test_five_judges(self):
        result, error = ev.judge_scores(judge())
        self.assertIsNone(error)
        self.assertEqual(result["TF"], 8)

    def test_partial_excluded(self):
        x = judge()
        x["eval_result"]["runs"].pop()
        self.assertIsNone(ev.judge_scores(x)[0])

    def test_boolean_not_score(self):
        x = judge()
        x["eval_result"]["runs"][0]["result"]["grounding"] = True
        self.assertIsNone(ev.judge_scores(x)[0])

    def test_out_of_range(self):
        self.assertIsNone(ev.judge_scores(judge(11))[0])

    def test_aggregate_tamper(self):
        x = judge()
        x["eval_result"]["aggregate"]["task_fulfillment_mean"] = 9
        self.assertIsNone(ev.judge_scores(x)[0])

    def test_unrounded_mean(self):
        x = judge()
        x["eval_result"]["runs"][0]["result"]["task_fulfillment"] = 9
        x["eval_result"]["aggregate"]["task_fulfillment_mean"] = 8.2
        self.assertEqual(ev.judge_scores(x)[0]["TF"], 8.2)

    def test_equal_task_weights(self):
        self.assertEqual(
            ev.weighted(
                [{"task_id": 1, "x": 2}, {"task_id": 1, "x": 2}, {"task_id": 2, "x": 10}], "x"
            ),
            6,
        )

    def test_recovery(self):
        m, s = data()
        out = ev.summarize(m, s, [])
        row = next(
            x
            for x in out["recovery_retention"]
            if x["stage"] == "late"
            and x["strategy"] == "selective_patch"
            and x["subgroup"] == "changed"
        )
        self.assertEqual(row["delta_vs_no_update_same_stage"], 2)

    def test_common_set_and_missing_triplet(self):
        m, s = data()
        del s[105, "late", "full_rewrite", 0]
        out = ev.summarize(m, s, [])
        self.assertTrue(all(x["TF"] is None for x in out["main_results"] if x["stage"] == "late"))
        self.assertTrue(all(x["upstream_population"] is None for x in out["ecs"]))
        self.assertEqual(len(out["exclusions"]), 3)

    def test_uncertain_not_recovery(self):
        m, s = data()
        m["tasks"][0]["transitions"]["late"]["label"] = "uncertain"
        out = ev.summarize(m, s, [])
        self.assertTrue(
            all(x["matched_cells"] == 0 for x in out["recovery_retention"] if x["stage"] == "late")
        )

    def test_deduplicate_update_cost(self):
        x = {
            "artifact_id": "one",
            "strategy": "full_rewrite",
            "tokens": 10,
            "seconds": 2,
            "usd": None,
        }
        out = ev.update_costs({"updates": [x, copy.deepcopy(x)]}, [])
        row = out[1]
        self.assertEqual(row["tokens_total"], 10)
        self.assertIsNone(row["usd_total"])

    def test_conflicting_cost(self):
        x = {"artifact_id": "one", "strategy": "full_rewrite", "tokens": 10}
        y = dict(x, tokens=12)
        with self.assertRaises(ValueError):
            ev.update_costs({"updates": [x, y]}, [])

    def test_unknown_not_zero(self):
        x = {"artifact_id": "one", "strategy": "full_rewrite", "tokens": None}
        self.assertIsNone(ev.update_costs({"updates": [x]}, [])[1]["tokens_total"])

    def test_demo_blocked_in_formal_mode(self):
        m, _ = data()
        with self.assertRaises(ValueError):
            ev.validate_manifest(m)
        ev.validate_manifest(m, True)

    def test_development_task_blocked(self):
        m, _ = data()
        m["tasks"][0]["task_id"] = 139
        with self.assertRaises(ValueError):
            ev.validate_manifest(m, True)

    def test_file_hash_tamper(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "r.json"
            p.write_text("{}")
            e = {"result_path": "r.json", "result_path_sha256": ev.digest(p)}
            ev.checked_file(Path(tmp), e, "result_path")
            p.write_text('{"changed":true}')
            with self.assertRaises(ValueError):
                ev.checked_file(Path(tmp), e, "result_path")

    def test_end_to_end_and_duplicate_selection(self):
        m, _ = data()
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            entries = []
            for v in ev.STAGES:
                for s in ev.STRATEGIES:
                    stem = v + "-" + s
                    result = {
                        "task_id": 105,
                        "version": v,
                        "strategy": s,
                        "seed": 0,
                        "status": "evaluated",
                        "execution_status": "completed",
                        "judge_status": "complete",
                        "TF": 8,
                        "PE": 7,
                        "config_sha256": "a" * 64,
                        "cost": {},
                    }
                    rp = base / (stem + ".json")
                    rp.write_text(json.dumps(result))
                    ep = base / (stem + "-eval.json")
                    ep.write_text(json.dumps(judge()))
                    entries.append(
                        {
                            "task_id": 105,
                            "stage": v,
                            "strategy": s,
                            "repeat_id": 0,
                            "attempt_id": 0,
                            "experiment_id": m["experiment_id"],
                            "comparison_config_file_sha256": "test-only",
                            "expected_config_sha256": "a" * 64,
                            "selected_for_analysis": True,
                            "result_path": rp.name,
                            "result_path_sha256": ev.digest(rp),
                            "eval_path": ep.name,
                            "eval_path_sha256": ev.digest(ep),
                        }
                    )
            expected, selected, attempts = ev.load_runs(m, {"runs": entries}, base)
            self.assertEqual(len(selected), 9)
            self.assertEqual(
                ev.summarize(m, selected, attempts)["ecs"][0]["upstream_population"], 8
            )
            duplicate = copy.deepcopy(entries[0])
            duplicate.update(attempt_id=1, retry_evidence="test only")
            with self.assertRaises(ValueError):
                ev.load_runs(m, {"runs": entries + [duplicate]}, base)


if __name__ == "__main__":
    unittest.main()
