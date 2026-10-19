import copy

import pytest

from integration.baselines import adapt, build_knowledge

pytestmark = pytest.mark.usefixtures("mock_baseline_llm")

REQUIRED_COST_FIELDS = {
    "model_calls",
    "input_tokens",
    "output_tokens",
    "api_cost_usd",
    "elapsed_seconds",
    "update_operations",
}


def make_tool(tool_id, name, description, parameters=None):
    return {
        "id": tool_id,
        "name": name,
        "description": description,
        "parameters": parameters or {},
    }


def make_old_metadata():
    return {
        "tools": [
            make_tool(
                "tool_001",
                "search",
                "Search the web",
                {"query": {"type": "string", "required": True}},
            ),
            make_tool(
                "tool_002",
                "calculator",
                "Perform calculations",
                {"expression": {"type": "string", "required": True}},
            ),
        ]
    }


def make_old_knowledge():
    return build_knowledge(make_old_metadata())


def make_new_metadata():
    return {
        "tools": [
            make_tool(
                "tool_001",
                "search",
                "Search the web",
                {"query": {"type": "string", "required": True}},
            ),
            make_tool(
                "tool_003",
                "translate",
                "Translate text",
                {"text": {"type": "string", "required": True}},
            ),
        ]
    }


def get_tool_names(knowledge):
    """从统一的 knowledge 结构中提取工具名称。"""
    return {tool["name"] for tool in knowledge["tools"]}


def check_common_output(new_knowledge, diff_log, update_cost):
    """检查三个返回值的基本结构。"""
    assert new_knowledge is not None
    assert diff_log is not None
    assert isinstance(update_cost, dict)

    missing_fields = REQUIRED_COST_FIELDS - set(update_cost.keys())
    assert not missing_fields, f"缺少成本字段: {missing_fields}"

    assert update_cost["model_calls"] >= 0
    assert update_cost["input_tokens"] >= 0
    assert update_cost["output_tokens"] >= 0
    assert update_cost["api_cost_usd"] is None or update_cost["api_cost_usd"] >= 0
    assert update_cost["elapsed_seconds"] >= 0
    assert update_cost["update_operations"] >= 0


def test_no_update_preserves_old_knowledge():
    """No Update 应该原样保留旧知识。"""
    old_knowledge = make_old_knowledge()
    new_metadata = make_new_metadata()
    old_knowledge_before = copy.deepcopy(old_knowledge)

    new_knowledge, diff_log, update_cost = adapt(
        old_knowledge=old_knowledge,
        new_metadata=new_metadata,
        strategy="no_update",
        context=None,
    )

    check_common_output(new_knowledge, diff_log, update_cost)

    assert old_knowledge == old_knowledge_before
    assert new_knowledge == old_knowledge
    assert "translate" not in get_tool_names(new_knowledge)
    assert update_cost["update_operations"] == 0


def test_no_update_ignores_new_metadata():
    """新版 metadata 改变时，No Update 的结果也不能改变。"""
    old_knowledge = make_old_knowledge()

    metadata_a = make_new_metadata()
    metadata_b = copy.deepcopy(metadata_a)
    metadata_b["tools"].append(make_tool("tool_004", "weather", "Get weather information"))

    result_a, _, _ = adapt(
        old_knowledge=old_knowledge,
        new_metadata=metadata_a,
        strategy="no_update",
        context=None,
    )
    result_b, _, _ = adapt(
        old_knowledge=old_knowledge,
        new_metadata=metadata_b,
        strategy="no_update",
        context=None,
    )

    assert result_a == result_b
    assert "weather" not in get_tool_names(result_b)


def test_full_rewrite_uses_new_metadata():
    """Full Rewrite 应该根据新版 metadata 完整重建知识。"""
    old_knowledge = make_old_knowledge()
    new_metadata = make_new_metadata()

    new_knowledge, diff_log, update_cost = adapt(
        old_knowledge=old_knowledge,
        new_metadata=new_metadata,
        strategy="full_rewrite",
        context=None,
    )

    check_common_output(new_knowledge, diff_log, update_cost)

    result_names = get_tool_names(new_knowledge)
    expected_names = get_tool_names(new_metadata)

    assert result_names == expected_names
    assert "calculator" not in result_names
    assert "translate" in result_names


def test_full_rewrite_handles_rename():
    """Full Rewrite 应该处理工具重命名。"""
    old_knowledge = make_old_knowledge()
    new_metadata = make_old_metadata()
    new_metadata["tools"][0]["name"] = "web_search"

    new_knowledge, diff_log, update_cost = adapt(
        old_knowledge=old_knowledge,
        new_metadata=new_metadata,
        strategy="full_rewrite",
        context=None,
    )

    check_common_output(new_knowledge, diff_log, update_cost)

    result_names = get_tool_names(new_knowledge)
    assert "web_search" in result_names
    assert "search" not in result_names


def test_unchanged_metadata():
    """没有 metadata 变化时，两种策略都应该可以正常运行。"""
    old_knowledge = make_old_knowledge()
    unchanged_metadata = make_old_metadata()

    no_update_result = adapt(
        old_knowledge=old_knowledge,
        new_metadata=unchanged_metadata,
        strategy="no_update",
        context=None,
    )
    full_rewrite_result = adapt(
        old_knowledge=old_knowledge,
        new_metadata=unchanged_metadata,
        strategy="full_rewrite",
        context=None,
    )

    check_common_output(*no_update_result)
    check_common_output(*full_rewrite_result)

    assert get_tool_names(no_update_result[0]) == {"search", "calculator"}
    assert get_tool_names(full_rewrite_result[0]) == {"search", "calculator"}


def test_invalid_strategy_is_rejected():
    """未知策略应该报错。"""
    with pytest.raises((ValueError, KeyError)):
        adapt(
            old_knowledge=make_old_knowledge(),
            new_metadata=make_new_metadata(),
            strategy="unknown_strategy",
            context=None,
        )
