"""Inventory current blinded external responses; does not decide causal comparability."""
import hashlib
import json
from collections import defaultdict
from pathlib import Path


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def main():
    folder = Path(__file__).resolve().parent
    requests, pages = defaultdict(list), defaultdict(list)
    manifest, errors, activation, full_texts = [], [], [], []
    packets = sorted((folder / "blind-inputs").glob("*.json"))
    for path in packets:
        packet = json.loads(path.read_text())
        rid = packet["review_id"]
        if "RT-2" not in packet["question"]:
            continue
        discovery = []
        for index, call in enumerate(packet["calls"]):
            tool = call["tool"].split("__")[0]
            args = json.loads(call["arguments"]) if isinstance(call["arguments"], str) else call["arguments"]
            result = call["result"]
            text = "\n".join(c.get("text", "") for c in result.get("content", []))
            if tool in ("resolve-library-id", "query-docs", "list-popular-libraries"):
                row = {"review_id": rid, "call_index": index, "tool": tool, "arguments": args,
                       "isError": result.get("isError"), "text_sha256": digest(text), "text_chars": len(text)}
                manifest.append(row)
                key = (tool, json.dumps(args, sort_keys=True))
                requests[key].append(row)
                if tool == "list-popular-libraries":
                    discovery.append({"call_index": index, "result_text": text, "isError": result.get("isError")})
                if result.get("isError") or text.lower().startswith(("error", "no documentation", "no libraries")):
                    errors.append({**row, "text": text})
            elif tool == "read_pdf":
                try:
                    decoded = json.loads(text)
                except ValueError:
                    errors.append({"review_id": rid, "tool": tool, "text": text})
                    continue
                for source in decoded.get("results", []):
                    if not source.get("success"):
                        errors.append({"review_id": rid, "tool": tool, "result": source})
                        continue
                    data = source["data"]
                    for page in data.get("page_texts", []):
                        pages[page["page"]].append((rid, page["text"]))
                    if "full_text" in data:
                        full_texts.append((rid, data["full_text"]))
        activation.append({"review_id": rid, "discovery_calls": len(discovery),
                           "calls": discovery, "tool_calls": len(packet["calls"])})
    comparisons = [{"tool": key[0], "arguments": json.loads(key[1]),
                    "review_ids": [r["review_id"] for r in values],
                    "texts_identical": len({r["text_sha256"] for r in values}) == 1}
                   for key, values in requests.items() if len(values) > 1]
    page_comparisons = [{"page": page, "review_ids": [r for r, _ in values],
                         "page_texts_identical": len({digest(text) for _, text in values}) == 1,
                         "full_text_contains": [{"review_id": rid, "all_page_variants_present":
                                                  all(text in full for _, text in values)}
                                                 for rid, full in full_texts]}
                        for page, values in sorted(pages.items())]
    print(json.dumps({"packet_count": len(packets), "method_and_scores_read": False,
                      "identical_request_comparisons": comparisons, "pdf_page_comparisons": page_comparisons,
                      "context7_and_pdf_errors": errors, "mechanism_activation": activation,
                      "tool_response_manifest": manifest,
                      "limits": "Only identical requests and overlapping local PDF text are directly compared. Different queries are agent choices; live content remains uncontrolled. Human review must decide whether any observed difference plausibly confounds the result."},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
