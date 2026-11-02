"""Run only six unexecuted Late calls, retaining native result validation errors."""
import asyncio
import json

from run_probes import FOLDER, ROOT, PLAN, save, sha, configure_runtime, sessions


async def main():
    work = FOLDER / "workspaces/late"
    work.mkdir(parents=True, exist_ok=False)
    plan = json.loads(PLAN.read_text())
    continuation = ROOT / "experiments/thinking-contract-probes-v1-continuation.json"
    for item in plan["source"]:
        assert sha(ROOT / item["path"]) == item["sha256"]
    configure_runtime(ROOT)
    save(FOLDER / "continuation-preexecution.json", {"freeze_commit": "8b49b7a",
         "plan_sha256": sha(PLAN), "continuation_sha256": sha(continuation), "model_calls": 0})
    rows = []
    async with sessions(ROOT, "late", [plan["server"]], work,
                        FOLDER / "late-stderr.log") as clients:
        client = clients[plan["server"]]
        save(FOLDER / "late-catalog.json",
             (await client.list_tools()).model_dump(mode="json", by_alias=True))
        original_validator = client._validate_tool_result
        captured = {}

        async def record_then_validate(name, result):
            captured["result"] = result.model_dump(mode="json", by_alias=True, exclude_none=True)
            await original_validator(name, result)

        client._validate_tool_result = record_then_validate
        for index, call in enumerate(plan["calls"]["late"], 1):
            captured.clear()
            row = {"stage": "late", "index": index, **call}
            try:
                row["result"] = (await client.call_tool(call["tool"], call["arguments"])).model_dump(
                    mode="json", by_alias=True, exclude_none=True)
                row["client_exception"] = None
            except Exception as exc:
                row["result"] = captured.get("result")
                row["client_exception"] = {"type": type(exc).__name__, "message": str(exc)}
            save(FOLDER / "late" / f"{index:02d}-{call['tool']}.json", row)
            rows.append(row)
    assert len(rows) == 6
    save(FOLDER / "late-observations.json", rows)
    print(json.dumps({"new_tool_calls": 6, "all_tool_calls": 12, "catalog_calls_total": 3,
                      "model_calls": 0, "late_client_exceptions": sum(bool(r["client_exception"]) for r in rows),
                      "late_tool_error_results": sum(bool((r["result"] or {}).get("isError")) for r in rows)}))


if __name__ == "__main__":
    asyncio.run(main())
