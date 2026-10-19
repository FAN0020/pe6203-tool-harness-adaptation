"""Synthetic fixtures for testing No Update and Full Rewrite baselines.

These fixtures use a temporary canonical dictionary format. They are intended
for local development before the real metadata format from Group A is fixed.
"""

from copy import deepcopy


def make_tool(tool_id, name, description, parameters=None):
    """Create one synthetic tool metadata record."""
    return {
        "id": tool_id,
        "name": name,
        "description": description,
        "parameters": parameters or {},
    }


def make_metadata(version, tools):
    """Create one metadata snapshot."""
    return {
        "version": version,
        "tools": deepcopy(tools),
    }


def make_knowledge(tools):
    """Create old_knowledge in the temporary canonical format."""
    return {
        "tools": deepcopy(tools),
    }


def make_case(
    name,
    old_tools,
    new_tools,
    expected_no_update_tools,
    expected_full_rewrite_tools,
    expected_operations,
):
    """Build one complete baseline test case."""
    return {
        "name": name,
        "old_knowledge": make_knowledge(old_tools),
        "old_metadata": make_metadata("old", old_tools),
        "new_metadata": make_metadata("new", new_tools),
        "expected_no_update_tools": list(expected_no_update_tools),
        "expected_full_rewrite_tools": list(expected_full_rewrite_tools),
        "expected_operations": list(expected_operations),
    }


def unchanged_case():
    """No metadata changes."""
    tools = [
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

    return make_case(
        name="unchanged",
        old_tools=tools,
        new_tools=tools,
        expected_no_update_tools=["search", "calculator"],
        expected_full_rewrite_tools=["search", "calculator"],
        expected_operations=[],
    )


def added_tool_case():
    """The new metadata adds one tool."""
    old_tools = [
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
    new_tools = old_tools + [
        make_tool(
            "tool_003",
            "translate",
            "Translate text",
            {"text": {"type": "string", "required": True}},
        )
    ]

    return make_case(
        name="added_tool",
        old_tools=old_tools,
        new_tools=new_tools,
        expected_no_update_tools=["search", "calculator"],
        expected_full_rewrite_tools=["search", "calculator", "translate"],
        expected_operations=["add"],
    )


def removed_tool_case():
    """The new metadata removes one tool."""
    old_tools = [
        make_tool("tool_001", "search", "Search the web"),
        make_tool("tool_002", "calculator", "Perform calculations"),
    ]
    new_tools = [
        make_tool("tool_001", "search", "Search the web"),
    ]

    return make_case(
        name="removed_tool",
        old_tools=old_tools,
        new_tools=new_tools,
        expected_no_update_tools=["search", "calculator"],
        expected_full_rewrite_tools=["search"],
        expected_operations=["remove"],
    )


def renamed_tool_case():
    """The tool keeps its stable ID but changes its name."""
    old_tools = [
        make_tool("tool_001", "search", "Search the web"),
    ]
    new_tools = [
        make_tool("tool_001", "web_search", "Search the web"),
    ]

    return make_case(
        name="renamed_tool",
        old_tools=old_tools,
        new_tools=new_tools,
        expected_no_update_tools=["search"],
        expected_full_rewrite_tools=["web_search"],
        expected_operations=["rename"],
    )


def parameter_changed_case():
    """The tool keeps its name but changes its parameters."""
    old_tools = [
        make_tool(
            "tool_001",
            "search",
            "Search the web",
            {"query": {"type": "string", "required": True}},
        ),
    ]
    new_tools = [
        make_tool(
            "tool_001",
            "search",
            "Search the web",
            {
                "query": {"type": "string", "required": True},
                "language": {"type": "string", "required": False},
            },
        ),
    ]

    return make_case(
        name="parameter_changed",
        old_tools=old_tools,
        new_tools=new_tools,
        expected_no_update_tools=["search"],
        expected_full_rewrite_tools=["search"],
        expected_operations=["parameter_change"],
    )


def description_changed_case():
    """The tool keeps its name and parameters but changes its description."""
    old_tools = [
        make_tool("tool_001", "search", "Search the web"),
    ]
    new_tools = [
        make_tool(
            "tool_001",
            "search",
            "Search the web and return ranked results",
        ),
    ]

    return make_case(
        name="description_changed",
        old_tools=old_tools,
        new_tools=new_tools,
        expected_no_update_tools=["search"],
        expected_full_rewrite_tools=["search"],
        expected_operations=["description_change"],
    )


def all_cases():
    """Return all synthetic baseline cases."""
    return [
        unchanged_case(),
        added_tool_case(),
        removed_tool_case(),
        renamed_tool_case(),
        parameter_changed_case(),
        description_changed_case(),
    ]
