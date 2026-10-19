import copy

from test_contract import module, record


def test_rules_and_output_schema_reach_agent_without_mutating_snapshot():
    old = record()
    old["usage_rules"] = ["Return dates in UTC"]
    old["output_schema"] = {"type": "object", "required": ["date"]}
    before = copy.deepcopy(old)
    tools, _ = module("runner").prepare_tools([old], "no_update")
    description = tools[0]["function"]["description"]
    assert "Return dates in UTC" in description
    assert '"required": ["date"]' in description
    assert old == before


def test_namespaced_tool_routes_are_unique_stable_and_frozen():
    a, b = record(), record()
    b.update(
        server_id="other",
        tool_id="other::old_tool",
        routing={"server_id": "other", "tool_name": "old_tool"},
    )
    prepare = module("runner").prepare_tools
    together, routes = prepare([a, b], "no_update", name_policy="namespaced")
    alone, _ = prepare([a], "no_update", name_policy="namespaced")
    names = [x["function"]["name"] for x in together]
    assert len(set(names)) == 2
    assert alone[0]["function"]["name"] == names[0]
    assert all(len(n) <= 64 for n in names)
    assert routes[names[1]] == {"server_id": "other", "tool_name": "old_tool"}


def test_long_names_on_same_server_keep_distinct_routes():
    a, b = record(), record()
    for item, ending in [(a, "first"), (b, "second")]:
        item["name"] = "tool_" + "x" * 60 + ending
        item["tool_id"] = item["server_id"] + "::" + item["name"]
        item["routing"]["tool_name"] = item["name"]
    tools, routes = module("runner").prepare_tools([a, b], "no_update", "namespaced")
    assert len(routes) == 2
    assert {r["tool_name"] for r in routes.values()} == {a["name"], b["name"]}
    assert all(len(t["function"]["name"]) <= 64 for t in tools)
