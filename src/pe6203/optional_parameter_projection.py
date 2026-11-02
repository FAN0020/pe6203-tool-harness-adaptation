"""Project certified no-effect optional choices out of model-facing knowledge.

Native schemas, dispatchers, argument forwarding and mandatory arguments remain
unchanged. This is a bounded research certificate, not a general dead-code proof.
"""

from .semantic_contract_maintenance import frozen_patch

TOOL = "math-mcp::validate_syntax"
HANDLER = "fe63b22756354f3249c450dbf113ccd8f24579654debf3e4412c3ce971ea2c39"
PROBES = "1aa531d12f560a7cce4c87c1f84a9a3f5e9fa7a9edb3221ae8e2b92a97f215c7"
SERVERS = {
    "middle": "881897c762485ab29df7432ac7ffd60c4564428a2b820c0d96d7f990a0efdb66",
    "late": "96a4f655eda70b22aa1d31192a5a72f507d52eeaa4799d3a6bfaff4e9a60c8be",
}
ERASE = {
    "middle": ["detailed", "allow_variables"],
    "late": ["detailed", "show_ast", "check_balanced", "max_depth"],
}


def project_optional(old, target, feedback):
    knowledge, _ = frozen_patch(old, target, feedback, False)
    if old == target or not any(t["server_id"] == "math-mcp" for t in target["tools"]):
        return knowledge, []
    stage = target["version"]
    rows = [r for r in feedback if r.get("stage") == stage and r.get("server") == "math-mcp"]
    if stage not in ERASE or len(rows) != 1:
        raise ValueError("No certified projection for this catalog")
    expected = {
        "kind": "source_certified_optional_projection_v1",
        "handler_sha256": HANDLER,
        "server_sha256": SERVERS[stage],
        "handler_reads": ["expression"],
        "erase": ERASE[stage],
        "omission_equivalence_passed": True,
        "native_results_sha256": PROBES,
    }
    if rows[0]["result"].get("projection_certificate") != expected:
        raise ValueError("Uncertified field erasure or native behavior")
    tool = next(t for t in knowledge["tools"] if t["tool_id"] == TOOL)
    schema = tool["parameters"]
    changes = []
    for name in ERASE[stage]:
        if name in schema.get("required", []) or name not in schema["properties"]:
            raise ValueError("Cannot erase a required or absent argument")
        changes.append(
            {
                "operation": "project_ineffective_optional_parameter",
                "tool_id": TOOL,
                "parameter": name,
                "before": schema["properties"].pop(name),
                "basis": TOOL,
                "evidence": PROBES,
                "scope": "model-facing knowledge only; native dispatcher remains unchanged",
            }
        )
    return knowledge, changes
