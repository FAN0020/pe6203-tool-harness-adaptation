"""Independent exact-body and native-state checks for the frozen admission."""
import json
import re


def unpack(result):
    if result.get("isError"):
        raise ValueError("Native MCP isError")
    texts = [c["text"] for c in result.get("content", []) if c.get("type") == "text"]
    if len(texts) != 1:
        raise ValueError("Expected one native JSON text")
    inner = json.loads(texts[0])
    if inner.get("success") is not True:
        raise ValueError("Native inner success not true")
    return inner


def check_document(text, pages, dark=False):
    errors = []
    positions = []
    for page in pages:
        body = page["body"]
        if text.count(body) != 1:
            errors.append(f"body{page['index']}: exact occurrence count !=1")
        positions.append(text.find(body))
    if positions != sorted(positions):
        errors.append("Body order changed")
    if dark:
        first = re.match(r"\A---\s*\n(.*?)\n---(?:\n|$)", text, re.S)
        if not first or not re.search(r"^theme: dark\s*$", first.group(1), re.M):
            errors.append("Root theme is not dark")
    return errors


def check_records(result, pages):
    try:
        records = unpack(result)["output"]
    except (ValueError, KeyError, TypeError) as exc:
        return [str(exc)]
    if not isinstance(records, list) or len(records) != len(pages):
        return ["Native page count mismatch"]
    errors = []
    for record, page in zip(records, pages, strict=True):
        if record.get("index") != page["index"] or record.get("layout") != page["layout"]:
            errors.append(f"page{page['index']}: index/layout mismatch")
        if record.get("content", "").count(page["body"]) != 1:
            errors.append(f"page{page['index']}: native exact body missing")
    return errors
