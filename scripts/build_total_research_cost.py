"""Receipt-ID deduplication across the historical audit and five new rounds."""

import hashlib
import json
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
E = ROOT / "results/evidence/unified-reaudit-20261102"
RAW = ROOT / "results/raw"
NAMES = [
    "evidence-dictionary-pilot-20261102",
    "evidence-contrastive-pilot-ready-20261102",
    "capability-consolidation-pilot-20261102",
    "relational-probe-memory-pilot-20261102",
    "pruned-episode-memory-pilot-20261102",
]


def main():
    historical = json.loads((E / "cost-receipts.json").read_text())
    amounts = {r["id"]: Decimal(r["known_usd"]) for r in historical}
    initial = set(amounts)
    ledgers = []
    for name in NAMES:
        plan = json.loads((RAW / name / "plan.json").read_text())
        ledgers.append(ROOT / plan["config"]["spend_guard"]["ledger"])
    ledgers.append(RAW / "relational-probe-memory-updater-costs-20261102/spend-ledger.json")
    new = []
    sources = []
    for p in ledgers:
        d = json.loads(p.read_text())
        assert not d["blocked"]
        assert all(r["status"] == "settled" for r in d["requests"])
        subtotal = sum((Decimal(r["actual_usd"]) for r in d["requests"]), Decimal(0))
        assert subtotal == Decimal(d["known_usd"])
        sources.append(
            {
                "ledger": str(p.relative_to(ROOT)),
                "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                "requests": len(d["requests"]),
                "known_usd": str(subtotal),
                "new_unknown": 0,
            }
        )
        for r in d["requests"]:
            identity = r["response_id"]
            value = Decimal(r["actual_usd"])
            assert identity
            if identity in amounts:
                assert amounts[identity] == value
            else:
                amounts[identity] = value
            assert identity not in initial, (
                "New-round request already in frozen historical snapshot"
            )
            new.append(
                {"id": identity, "known_usd": str(value), "source": str(p.relative_to(ROOT))}
            )
    assert len(new) == len({r["id"] for r in new})
    out = {
        "historical_receipts": len(initial),
        "new_receipts": len(new),
        "union_priced_receipts": len(amounts),
        "historical_known_lower_bound_usd": str(
            sum((Decimal(r["known_usd"]) for r in historical), Decimal(0))
        ),
        "new_known_usd": str(sum((Decimal(r["known_usd"]) for r in new), Decimal(0))),
        "union_known_lower_bound_usd": str(sum(amounts.values(), Decimal(0))),
        "new_unknown_requests": 0,
        "historical_unknowns": "Three unresolved ledger requests plus early failed actor requests without IDs; see cost-audit.json. Reservations are not actual charges and not a spending cap.",
        "sources": sources,
        "historical_receipt_index_sha256": hashlib.sha256(
            (E / "cost-receipts.json").read_bytes()
        ).hexdigest(),
        "key_limit_note": "Aggregate key usage verifies this last trial delta only; it cannot resolve old requests without receipts.",
    }
    (E / "total-cost-audit.json").write_text(json.dumps(out, indent=2) + "\n")
    (E / "new-cost-receipts.json").write_text(json.dumps(new, indent=2) + "\n")
    print(
        json.dumps(
            {
                k: v
                for k, v in out.items()
                if k not in ["sources", "historical_receipt_index_sha256"]
            }
        )
    )


if __name__ == "__main__":
    main()
