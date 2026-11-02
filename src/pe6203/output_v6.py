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
    # Avoid repeating the entire directory in the global decoder schema.
    # Local packets already contain a bounded registry: literal membership is
    # decoder-constrained as well as independently checked by program admission.
    if phase == "global_screen":
        return deepcopy(SCREEN)
    result = deepcopy(PATCH)
    evidence_ids = sorted(payload["evidence_registry"])
    basis_ids = sorted({c["change_id"] for c in payload["changes"]})
    selected_ids = sorted({r["tool_id"] for r in payload["selected"]})
    if not evidence_ids or not basis_ids or not selected_ids:
        raise ValueError("Local decoder schema requires evidence, changes and selected records")
    patch = result["properties"]["patches"]["items"]["properties"]
    patch["tool_id"] = {"type": "string", "enum": selected_ids}
    patch["basis"] = arr({"type": "string", "enum": basis_ids})
    patch["evidence_ids"] = arr({"type": "string", "enum": evidence_ids})
    patch["rules"]["items"]["properties"]["evidence_ids"] = arr(
        {"type": "string", "enum": evidence_ids}
    )
    # A position belongs to its own record. A global union of rule indices
    # would incorrectly permit [0] for an empty record when a peer has rules.
    branches = []
    for record in payload["selected"]:
        existing = record["rules"]
        if not isinstance(existing, list):
            raise ValueError("Selected existing rules must be a list")
        branch = deepcopy(result["properties"]["patches"]["items"])
        properties = branch["properties"]
        properties["tool_id"] = {"type": "string", "enum": [record["tool_id"]]}
        retained = {"type": "array", "items": {"type": "integer"},
                    "maxItems": len(existing)}
        if existing:
            retained["items"]["enum"] = list(range(len(existing)))
        # maxItems:0 forces [], without an invalid empty enum. Uniqueness,
        # sorting and all semantic admission remain independent program checks.
        properties["retain_rule_indices"] = retained
        branches.append(branch)
    result["properties"]["patches"]["items"] = {"anyOf": branches}
    # These enums prevent invented handles, not wrong semantic inferences or
    # out-of-scope citations. Those still require the unchanged program checks.
    selector_ids = sorted(set(selected_ids) | {c["tool_id"] for c in payload["changes"]})
    result["properties"]["need_evidence"]["items"]["properties"]["tool_id"] = {
        "type": "string", "enum": selector_ids
    }
    # The pointer is relative to this one catalog field, not the prompt
    # envelope. Changed leaves are already supplied by the program. Further
    # model requests name the field root; this does not upload a global catalog.
    result["properties"]["need_evidence"]["items"]["properties"]["pointer"] = {
        "type": "string", "enum": [""]
    }
    return result


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
