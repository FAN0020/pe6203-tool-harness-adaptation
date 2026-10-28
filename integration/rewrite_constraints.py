"""Conservative guards for machine-readable limits found in supplied metadata.

These checks cover selected failure patterns, not complete semantic equivalence.
They neither repair model output nor change benchmark schemas.
"""

import re

POLICY_VERSION = "metadata-constraints-v2"
_MAX_CHARS = re.compile(r"\bmax(?:imum)?(?:\s+of)?\s+(\d+)\s+(?:characters|chars)\b", re.I)
_ADVISORY = re.compile(r"\brecommend(?:ed)?|\bsuggest(?:ed)?|\bpreferably|\bideally", re.I)
_NULL_HINT = re.compile(r"\b(?:use|pass|set)\s+null\b|\bnull\s*/\s*empty\b", re.I)


class RewriteConstraintError(ValueError):
    def __init__(self, issues):
        super().__init__("Rewritten description failed metadata constraint checks")
        self.issues = issues


def _properties(schema, path="parameters"):
    if not isinstance(schema, dict):
        return
    for field, node in schema.get("properties", {}).items():
        if not isinstance(node, dict):
            continue
        location = f"{path}.properties.{field}"
        yield field, node, location
        yield from _properties(node, location)
        yield from _properties(node.get("items"), location + ".items")


def build_rewrite_checks(tools):
    """Use only the allowed tool catalog, including parameter descriptions."""
    checks = []
    for tool in tools:
        limits, conflicts = [], []
        for field, node, path in _properties(tool.get("parameters", {})):
            description = node.get("description", "")
            if not isinstance(description, str):
                description = ""
            maximum = node.get("maxLength")
            if type(maximum) is int and maximum >= 0:
                limits.append(
                    {"field": field, "max_characters": maximum, "source": path + ".maxLength"}
                )
            else:
                # A source already labelled advisory is not promoted to a hard limit.
                for sentence in re.split(r"(?<=[.!?])\s+|\n", description):
                    if _ADVISORY.search(sentence):
                        continue
                    for match in _MAX_CHARS.finditer(sentence):
                        limits.append(
                            {
                                "field": field,
                                "max_characters": int(match.group(1)),
                                "source": path + ".description",
                            }
                        )
            allowed_type = node.get("type")
            nonnullable = isinstance(allowed_type, str) and allowed_type != "null"
            nonnullable |= isinstance(allowed_type, list) and "null" not in allowed_type
            # Union schemas need a separate interpretation; do not guess their nullability.
            if nonnullable and not any(k in node for k in ("anyOf", "oneOf", "allOf")):
                if _NULL_HINT.search(description):
                    conflicts.append(
                        {
                            "field": field,
                            "issue": "description_mentions_null_but_schema_excludes_null",
                            "schema_type": allowed_type,
                            "source": path,
                        }
                    )
        if limits or conflicts:
            checks.append(
                {"name": tool["name"], "character_limits": limits, "metadata_conflicts": conflicts}
            )
    return checks


def validate_description(description, check):
    """Reject missing/weakened character limits and propagation of null conflicts."""
    issues = []
    sentences = re.split(r"(?<=[.!?])\s+|[;\n]", description)
    for limit in check["character_limits"]:
        field, number = limit["field"], str(limit["max_characters"])
        field_pattern = re.compile(r"(?<!\w)" + re.escape(field) + r"(?!\w)", re.I)
        bound = re.compile(
            rf"(?:\bmax(?:imum)?(?:\s+of)?|\bat\s+most|\bno\s+more\s+than|"
            rf"\bnot\s+exceed|\bcannot\s+exceed|\bup\s+to|<=)\s*{number}\s*"
            rf"(?:characters|chars)\b|\b{number}\s*(?:characters|chars)\s+or\s+(?:less|fewer)\b",
            re.I,
        )
        candidates = [sentence for sentence in sentences if field_pattern.search(sentence)]
        unsupported = re.compile(r"not\s+(?:a\s+)?(?:hard|mandatory)|soft\s+limit", re.I)
        weakened = any(
            bound.search(sentence) and (_ADVISORY.search(sentence) or unsupported.search(sentence))
            for sentence in candidates
        )
        preserved = any(
            bound.search(sentence)
            and not _ADVISORY.search(sentence)
            and not unsupported.search(sentence)
            for sentence in candidates
        )
        if weakened or not preserved:
            issues.append(
                {
                    "tool": check["name"],
                    "field": field,
                    "issue": "character_limit_weakened" if weakened else "character_limit_missing",
                    "max_characters": limit["max_characters"],
                    "source": limit["source"],
                }
            )
    if check["metadata_conflicts"] and re.search(r"\bnull\b", description, re.I):
        # Deliberately conservative: ask the model to describe accepted types without
        # repeating 'null' for a conflicting tool. Negation parsing is not a semantic proof.
        issues.extend(
            {
                "tool": check["name"],
                "field": conflict["field"],
                "issue": "null_conflict_repeated_in_description",
                "source": conflict["source"],
            }
            for conflict in check["metadata_conflicts"]
        )
    if issues:
        raise RewriteConstraintError(issues)
