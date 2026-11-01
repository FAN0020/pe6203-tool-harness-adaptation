"""Deterministic synthetic training inputs; evaluator oracles live separately."""
import hashlib
import json
import random
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[2]


def write(path, value):
    data = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() != data:
        raise ValueError(f"Refusing to replace frozen data: {path}")
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def generate():
    # The original task's server inventory only, never its question or answer.
    catalog = json.loads((ROOT / "tests/fixtures/prefix-workflow-catalogs.json").read_text())["457"]["late"]
    servers = {}
    for t in catalog["tools"]:
        servers.setdefault(t["server_id"], []).append(t["name"])
    manifest = {}
    for task_id, names, counts, latency, prices, volume, budget, limit in [
        (900201, ["Kestrel", "Spruce"], [200, 200], [140, 270], ["0.031", "0.049"], 80000, 4000, 200),
        (900202, ["Larch", "Willow"], [240, 300], [180, 260], ["0.026", "0.061"], 100000, 7000, 300),
    ]:
        seed = task_id - 100000
        rng = random.Random(seed)
        success = [rng.randint(int(n * lo), int(n * hi)) for n, lo, hi in zip(counts, [.80, .92], [.88, .97])]
        records = [{"method": name, "trials": n, "successful": s, "p95_ms": l, "usd_per_query": p}
                   for name, n, s, l, p in zip(names, counts, success, latency, prices)]
        question = (
            "Create and save a professional four-slide, six-minute decision briefing using Slidev, with a consistent dark design. "
            "This is a controlled synthetic training task: all organizations, methods and measurements below are fictional. "
            "Use these complete source notes; no external information is needed. The audience must choose a pilot option. "
            "Cover context and evaluation limits, present both methods' final evidence, compare calculated success rates and monthly usage costs, "
            "and recommend an option with limitations and next steps. Explain which methods satisfy BOTH constraints. "
            "Give success rates rounded to one decimal place and exact monthly query costs; use the final audited counts below. "
            "Choose the method with higher observed success rate among those meeting both latency and monthly cost limits. "
            "Do not portray small offline trials as established production reliability or present proposed next steps as measured results. "
            "Persist the actual presentation in the workspace and identify the saved artifact in the final answer.\n\n"
            f"Planned monthly volume: {volume} queries. Monthly query-cost limit: USD {budget}. Maximum p95 latency: {limit} ms. "
            "Only query costs are included; staffing, infrastructure and confidence intervals have not been estimated. "
            "Both methods ran on the same fixed hardware and task family, with independent test samples.\n"
            + "\n".join(f"FINAL AUDITED: {r['method']}: {r['successful']} successful out of {r['trials']} trials; p95 {r['p95_ms']} ms; USD {r['usd_per_query']} per query." for r in records)
            + f"\nSuperseded preliminary note: {names[0]} had {success[0]+5}/{counts[0]} successes before duplicate records were removed. "
            "This earlier figure is not valid for the decision."
        )
        expected = []
        for r in records:
            rate = (Decimal(r["successful"]) / r["trials"] * 100).quantize(Decimal(".1"), rounding=ROUND_HALF_UP)
            cost = Decimal(r["usd_per_query"]) * volume
            expected.append({**r, "success_percent": str(rate), "monthly_usd": str(cost),
                             "feasible": r["p95_ms"] <= limit and cost <= budget})
        best = max((r for r in expected if r["feasible"]), key=lambda r: Decimal(r["successful"]) / r["trials"])["method"]
        task = {"idx": task_id, "extension_id": f"ext-experience-brief-{task_id}-v1", "dataset_kind": "controlled_synthetic_extension", "question": question, "servers": servers}
        manifest[f"task-{task_id}.json"] = write(BASE / f"task-{task_id}.json", task)
        oracle = {"task_id": task_id, "seed": seed, "rows": expected, "recommendation": best,
                  "source_records": records, "monthly_volume": volume, "budget": budget, "latency_limit": limit,
                  "pages": 4, "status": "evaluation_only_never_agent_or_updater"}
        manifest[f"evaluation/oracle-{task_id}.json"] = write(BASE / f"evaluation/oracle-{task_id}.json", oracle)
    write(BASE / "data-manifest.json", manifest)
    print(json.dumps({"generated_files": len(manifest), "model_calls": 0}))


if __name__ == "__main__":
    generate()
