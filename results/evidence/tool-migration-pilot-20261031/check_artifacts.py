"""Extract factual evidence; Swift parsing only, never execute generated code."""

import hashlib
import json
import re
import subprocess
import tarfile
import tempfile
from pathlib import Path

FOLDER = Path(__file__).resolve().parent


def main():
    archive = FOLDER / "raw-trial.tar.gz"
    cells = []
    with tarfile.open(archive) as tar:
        names = {m.name for m in tar if m.isfile()}
        for name in sorted(n for n in names if n.endswith("/run/raw_trace.json")):
            trace = json.load(tar.extractfile(name))
            result = json.load(tar.extractfile(name.removesuffix("raw_trace.json") + "result.json"))
            answer = trace.get("answer") or ""
            blocks = re.findall(r"```swift[^\n]*\n(.*?)```", answer, re.S)
            checks = []
            for i, code in enumerate(blocks):
                with tempfile.TemporaryDirectory(prefix="pe6203-swift-parse-") as tmp:
                    path = Path(tmp) / "Example.swift"
                    path.write_text(code)
                    try:
                        run = subprocess.run(
                            ["/usr/bin/swiftc", "-frontend", "-parse", str(path)],
                            capture_output=True,
                            text=True,
                            timeout=15,
                            env={"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "HOME": tmp},
                        )
                        check = {
                            "block": i,
                            "source_sha256": hashlib.sha256(code.encode()).hexdigest(),
                            "parses": run.returncode == 0,
                            "exit_code": run.returncode,
                            "diagnostic": run.stderr.replace(tmp, "<temporary>")[:4000],
                        }
                    except (OSError, subprocess.TimeoutExpired) as exc:
                        check = {"block": i, "parses": None, "error": type(exc).__name__}
                    checks.append(check)
            observations = []
            for event in trace["events"]:
                if event["type"] != "tool_result":
                    continue
                tool = event["call"]["function"]["name"].rsplit("__", 1)[0]
                payload = event["result"]
                text = "\n".join(
                    c.get("text", "") for c in payload.get("content", []) if c.get("type") == "text"
                )
                semantic_error = text.startswith(
                    ("Error ", "Error:", "Error searching", "Error reading")
                )
                try:
                    decoded = json.loads(text)
                except ValueError:
                    decoded = None
                if isinstance(decoded, dict) and decoded.get("error"):
                    semantic_error = True
                observations.append(
                    {
                        "round": event["round"],
                        "tool": tool,
                        "arguments": json.loads(event["call"]["function"]["arguments"]),
                        "structured_error": bool(payload.get("isError")),
                        "text_reports_error": semantic_error,
                        "text_characters": len(text),
                        "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
                        "preview": text[:220],
                    }
                )
            cells.append(
                {
                    "cell_id": name.split("/cells/")[1].split("/")[0],
                    "stage": result["version"],
                    "strategy": result["strategy"],
                    "execution_status": result["execution_status"],
                    "final_answer_characters": len(answer),
                    "swift_blocks": checks,
                    "unclosed_code_fence": answer.count("```") % 2 == 1,
                    "observations": observations,
                    "trace_member": name,
                }
            )
    print(
        json.dumps(
            {
                "source_archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
                "new_model_calls": 0,
                "generated_code_executed": False,
                "validation": "Swift6.3.3 frontend parse, per standalone fenced Swift block; no type checking, module resolution, macro expansion or runtime execution claimed. Examples may legitimately contain omitted model types or callbacks. Semantic review is separate.",
                "cells": cells,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
