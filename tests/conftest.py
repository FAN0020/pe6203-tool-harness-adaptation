"""Explicit mock of only the updater API boundary; never a production fallback."""

import json

import pytest

from integration import baselines


@pytest.fixture
def mock_baseline_llm(monkeypatch):
    requests = []

    def complete(messages, settings):
        requests.append((messages, settings))
        tools = json.loads(messages[-1]["content"])["tools"]
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
                                        "description": "Rewritten: " + t.get("description", ""),
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
