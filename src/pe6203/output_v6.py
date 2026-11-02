"""V6-only structured transport. Program admission remains independent/strict."""

from copy import deepcopy


def obj(properties):
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


def arr(item):
    return {"type": "array", "items": item}


STRING = {"type": "string"}
STRINGS = arr(STRING)
SELECTOR = obj(
    {
        "tool_id": STRING,
        "side": {"type": "string", "enum": ["old", "target"]},
        "field": {
            "type": "string",
            "enum": [
                "parameters",
                "output_schema",
                "description",
                "routing",
                "name",
                "usage_rules",
            ],
        },
        "pointer": STRING,
    }
)
SCREEN = obj(
    {
        "covered_tool_ids": STRINGS,
        "candidates": arr(
            obj(
                {
                    "tool_id": STRING,
                    "category": {
                        "type": "string",
                        "enum": ["potential", "uncertain", "program_review"],
                    },
                    "reason": STRING,
                    "basis": STRINGS,
                    "fields": arr(SELECTOR),
                }
            )
        ),
    }
)
PATCH = obj(
    {
        "patches": arr(
            obj(
                {
                    "tool_id": STRING,
                    "retain_rule_indices": arr({"type": "integer"}),
                    "rules": arr(
                        obj(
                            {
                                "kind": {
                                    "type": "string",
                                    "enum": [
                                        "documentation",
                                        "source_observation",
                                        "probe_observation",
                                        "guidance",
                                        "unknown",
                                        "conflict",
                                    ],
                                },
                                "text": STRING,
                                "evidence_ids": STRINGS,
                            }
                        )
                    ),
                    "reason": STRING,
                    "basis": STRINGS,
                    "evidence_ids": STRINGS,
                }
            )
        ),
        "need_evidence": arr(SELECTOR),
    }
)


def schema(phase, payload):
    # ID membership/exact coverage is checked by the independent program. Do
    # not repeat the global directory in decoder-schema enums.
    return deepcopy(SCREEN if phase == "global_screen" else PATCH)


def response_format(phase, payload):
    return {
        "type": "json_schema",
        "json_schema": {"name": "selective_v6", "strict": True, "schema": schema(phase, payload)},
    }


def request_completion(messages, settings):
    """Only V6 uses this entry; historical provider calls are unchanged."""
    if not settings.get("allow_metadata_api", False):
        raise ValueError("Explicit allow_metadata_api required for V6 structured requests")
    from openai import OpenAI

    from integration.model_api import model_id, nonthinking_options

    from .runner import credentials

    key, url = credentials(settings)
    with OpenAI(api_key=key, base_url=url, timeout=settings["timeout"], max_retries=0) as client:
        return client.chat.completions.create(
            model=model_id(settings["model"], url),
            messages=messages,
            temperature=settings["temperature"],
            max_tokens=settings["max_tokens"],
            response_format=settings["response_format"],
            extra_body=nonthinking_options(url),
        ).model_dump(mode="json")
