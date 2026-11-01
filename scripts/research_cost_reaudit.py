"""Deduplicate existing billing receipts; unresolved requests remain explicit.

No credential access, network requests, model generation or raw message output.
The broader ledger scope also contains course and diagnostic expenses, so it is
reported separately from matched-cohort actor/judge receipts.
"""
import json
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/evidence/unified-reaudit-20261102"


def read(path):
    return json.loads(path.read_text())


def response_projection(value):
    if isinstance(value, dict):
        if isinstance(value.get("id"), str) and value["id"].startswith("gen-") and "usage" in value:
            yield {"id": value["id"], "known_usd": (value.get("usage") or {}).get("cost")}
        else:
            for child in value.values():
                yield from response_projection(child)
    elif isinstance(value, list):
        for child in value:
            yield from response_projection(child)


def main():
    receipts, mismatches = {}, []
    def add(identity, cost, source, scope):
        if not identity:
            return
        amount = Decimal(str(cost)) if cost is not None else None
        if identity not in receipts:
            receipts[identity] = {"id": identity, "known_usd": str(amount) if amount is not None else None,
                                  "sources": [], "scopes": []}
        row = receipts[identity]
        previous = Decimal(row["known_usd"]) if row["known_usd"] is not None else None
        if previous is not None and amount is not None and abs(previous-amount) > Decimal("0.000000000001"):
            mismatches.append({"id":identity,"amounts":[str(previous),str(amount)],"source":source})
        if previous is None and amount is not None:
            row["known_usd"] = str(amount)
        if source not in row["sources"]:
            row["sources"].append(source)
        if scope not in row["scopes"]:
            row["scopes"].append(scope)
    for row in read(OUT / "response-receipts.json"):
        add(row["id"], row["known_usd"], row["cohort"] + "/" + row["cell_id"], "matched_cohort_actor_judge")
    ledger_files = sorted((ROOT / "results/raw").glob("**/*ledger*.json"))
    ledger_files += sorted((ROOT / "results/evidence").glob("*/*ledger*.json"))
    ledger_reports, unresolved = [], {}
    for p in ledger_files:
        if any(n in str(p) for n in ("evidence-dictionary", "evidence-contrastive", "capability-consolidation")):
            continue  # New round has its own independent accounting.
        d = read(p)
        if not isinstance(d, dict) or not isinstance(d.get("requests"), list):
            continue
        src = str(p.relative_to(ROOT))
        known = Decimal(0)
        statuses = defaultdict(int)
        for i, r in enumerate(d["requests"]):
            if not isinstance(r, dict):
                continue
            statuses[r.get("status", "unknown")] += 1
            if r.get("actual_usd") is not None:
                known += Decimal(str(r["actual_usd"]))
            identity = r.get("response_id")
            add(identity, r.get("actual_usd"), src, "broader_historical_ledger")
            if r.get("status") != "settled":
                key = (r.get("started_at"), r.get("request_sha256"))
                if key == (None, None):
                    key = (src, i)
                unresolved.setdefault(str(key), {"started_at":r.get("started_at"),
                    "request_sha256":r.get("request_sha256"), "status":r.get("status"),
                    "error_type":r.get("error_type"), "response_id":identity,
                    "reserved_usd":r.get("reserved_usd"), "sources":[]})["sources"].append(src)
        ledger_reports.append({"file":src,"requests":len(d["requests"]),"statuses":dict(statuses),
                               "recomputed_known_usd":str(known),"recorded_known_usd":d.get("known_usd")})
    audits = sorted((ROOT / "results/raw").glob("*/adaptations/*/*audit*.json"))
    audits += sorted((ROOT / "results/evidence").glob("*/*updater*audit*.json"))
    audits += sorted((ROOT / "results/evidence").glob("*/recovery/*audit*.json"))
    for p in audits:
        if any(n in str(p) for n in ("evidence-dictionary", "evidence-contrastive", "capability-consolidation")):
            continue
        for r in response_projection(read(p)):
            add(r["id"],r["known_usd"],str(p.relative_to(ROOT)),"updater_receipt")
    def aggregate(scope):
        chosen = [r for r in receipts.values() if scope is None or scope in r["scopes"]]
        return {"responses":len(chosen), "priced":sum(r["known_usd"] is not None for r in chosen),
                "known_usd":str(sum((Decimal(r["known_usd"]) for r in chosen if r["known_usd"] is not None),Decimal(0)))}
    out = {"deduplicated_union":aggregate(None),
           "matched_cohort_actor_judge":aggregate("matched_cohort_actor_judge"),
           "broader_historical_ledger":aggregate("broader_historical_ledger"),
           "updater_receipts":aggregate("updater_receipt"),
           "unresolved_ledger_requests":list(unresolved.values()),"amount_mismatches":mismatches,
           "ledger_checks":ledger_reports,
           "limits":["Overlapping scopes must not be added together.",
                     "Union is a known lower bound, not a settled total; earliest failed requests may lack ledger/response IDs.",
                     "Broader ledgers include course, generation-only and diagnostic work beyond the36 registry candidates.",
                     "Unknown reservations are neither actual charges nor hard upper bounds.",
                     "Current dictionary/contrastive/consolidation rounds excluded and reported separately.",
                     "Updater audit extraction exports only response IDs and usage.cost, never messages or hidden reasoning."]}
    (OUT / "cost-receipts.json").write_text(json.dumps(list(receipts.values()),indent=2)+"\n")
    (OUT / "cost-audit.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({k:v for k,v in out.items() if k not in ["ledger_checks","unresolved_ledger_requests"]},ensure_ascii=False))
    print("Unresolved ledger requests:",len(unresolved))


if __name__ == "__main__":
    main()
