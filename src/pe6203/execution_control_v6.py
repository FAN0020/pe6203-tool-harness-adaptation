"""Opt-in V6 delivery control; no task-specific answer or extra execution budget."""

from copy import deepcopy

VERSION = "v6-execution-control-1"
SYSTEM_RULE = (
    "Gather only observations needed to complete the requested deliverable. "
    "When the available observations are sufficient, deliver the result instead of "
    "expanding the investigation. Reuse successful observations when the inputs and "
    "environment have not changed; repeat a call only for a specific unresolved need. "
    "The final allowed generation round is reserved for the final deliverable, with "
    "no further tool actions. Distinguish observed results from untested claims. "
    "When an artifact output contract is active, artifact.source must contain the "
    "actual runnable source module with real line breaks and Python indentation. "
    "Encode line breaks as JSON newline escapes that decode to real newlines; do "
    "not flatten the implementation into a single prose or comment line. Put "
    "explanations and security recommendations in the top-level summary."
)
FINAL_REMINDER = (
    "This is the final generation round within the existing budget. No further tool "
    "actions are available. Deliver the requested result now using the observations "
    "already obtained. State any unresolved limitation rather than claiming an "
    "unobserved success. Follow the required final-output format."
)


def settings(value, max_rounds):
    if value is None:
        return None
    if not isinstance(value, dict) or value != {"version": VERSION}:
        raise ValueError("V6 execution control requires the exact supported version object")
    if type(max_rounds) is not int or max_rounds < 1:
        raise ValueError("V6 execution control requires a positive integer round budget")
    return {
        "version": VERSION,
        "max_generation_rounds": max_rounds,
        "reserved_final_rounds": 1,
        "extra_tool_rounds": 0,
        "artifact_format": "artifact-v1-strict-json",
        "artifact_tests_and_repair_budget_changed": False,
    }


def artifact_response_format():
    """Format only: the existing artifact extractor/tests remain authoritative."""
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "artifact_v1_delivery",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "artifact": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "enum": ["artifact.py"]},
                            "language": {"type": "string", "enum": ["python"]},
                            "source": {
                                "type": "string",
                                "minLength": 1,
                                "pattern": r"\n",
                                "description": (
                                    "Complete runnable Python source module, preserving "
                                    "real newline characters and indentation. Include "
                                    "actual statements and definitions, not a description "
                                    "or promise of code. Do not flatten code into a single "
                                    "comment line. JSON newline escapes must decode to "
                                    "real line breaks in this source string. Put all "
                                    "explanations and security recommendations in the "
                                    "top-level summary. Formatting constraints do not "
                                    "prove program correctness or safety."
                                ),
                            },
                        },
                        "required": ["path", "language", "source"],
                        "additionalProperties": False,
                    },
                    "summary": {"type": "string"},
                },
                "required": ["artifact", "summary"],
                "additionalProperties": False,
            },
        },
    }


def generation_options(control, round_number, artifact):
    if control is None:
        return {}
    options = {}
    if round_number == control["max_generation_rounds"]:
        options["tool_choice"] = "none"
    if artifact:
        # Any generation round may return the final answer before the last round.
        # response_format constrains that content while tool calls remain allowed.
        options["response_format"] = artifact_response_format()
    return deepcopy(options)
