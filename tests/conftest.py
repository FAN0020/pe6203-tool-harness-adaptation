"""Explicit mock of only the updater API boundary; never a production fallback."""

import json

import pytest

from integration import baselines


@pytest.fixture
def mock_baseline_llm(monkeypatch):
    requests = []

    def complete(messages, settings):
        requests.append((messages, settings))
        payload = json.loads(messages[-1]["content"])
        tools = payload["tools"]
        checks = {item["name"]: item for item in payload.get("rewrite_checks", [])}

        def description(tool):
            text = "Rewritten: " + tool.get("description", "")
            for limit in checks.get(tool["name"], {}).get("character_limits", []):
                text += f" {limit['field']} has a maximum of {limit['max_characters']} characters."
            return text

        return {
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {
                        "content": json.dumps(
                            {
                                "tools": [
                                    {
                                        "name": t["name"],
                                        "description": description(t),
                                        "usage_rules": t.get("usage_rules", []),
                                    }
                                    for t in tools
                                ]
                            }
                        )
                    },
                }
            ],
            "usage": {"prompt_tokens": 101, "completion_tokens": 50, "total_tokens": 151},
        }

    monkeypatch.setattr(baselines, "_request_completion", complete)
    return requests
