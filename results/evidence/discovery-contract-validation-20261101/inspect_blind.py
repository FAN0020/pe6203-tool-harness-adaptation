"""Read one current blinded packet without loading conditions or rating files."""
import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("review_id")
    parser.add_argument("section", choices=("overview", "memory", "docs", "charts", "call"))
    parser.add_argument("--index", type=int)
    args = parser.parse_args()
    folder = Path(__file__).resolve().parent
    packet = json.loads((folder / "blind-inputs" / f"{args.review_id}.json").read_text())
    if args.section == "overview":
        print(json.dumps({"id": args.review_id, "question": packet["question"],
                          "answer": packet["answer"], "artifacts": packet["artifacts"]}, ensure_ascii=False))
        for index, call in enumerate(packet["calls"]):
            payload = call["arguments"]
            if any(name in call["tool"] for name in ("create_entities", "create_relations", "add_observations")):
                payload = f"[write arguments {len(str(payload))} characters; inspect actual memory separately]"
            print(json.dumps({"index": index, "tool": call["tool"], "arguments": payload,
                              "isError": call["result"].get("isError"),
                              "result_chars": len(json.dumps(call["result"], ensure_ascii=False))}, ensure_ascii=False))
    elif args.section == "memory":
        for artifact in packet["artifacts"]:
            print((folder / "blind-artifacts" / args.review_id / artifact["path"]).read_text())
        if not packet["artifacts"]:
            print("No persisted memory artifact.")
    elif args.section == "call":
        assert args.index is not None
        print(json.dumps(packet["calls"][args.index], ensure_ascii=False, indent=2))
    else:
        for index, call in enumerate(packet["calls"]):
            match = ("query_docs" in call["tool"] or "query-docs" in call["tool"])
            if args.section == "charts":
                match = "generate_" in call["tool"]
            if match:
                print("CALL", index)
                print(json.dumps(call, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
