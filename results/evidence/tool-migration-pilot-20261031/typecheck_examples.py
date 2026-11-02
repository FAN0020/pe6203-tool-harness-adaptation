"""Offline checks of selected answer fragments, with explicit adaptation provenance.

Does not execute generated Swift, change historical answers, or rescore judges.
"""

import hashlib
import json
import re
import subprocess
import tarfile
import tempfile
from pathlib import Path

FOLDER = Path(__file__).resolve().parent


def main():
    cases = []
    with tarfile.open(FOLDER / "raw-trial.tar.gz") as tar:
        for member in sorted(m.name for m in tar if m.name.endswith("/run/raw_trace.json")):
            trace = json.load(tar.extractfile(member))
            cell = member.split("/cells/")[1].split("/")[0]
            blocks = re.findall(r"```swift[^\n]*\n(.*?)```", trace["answer"], re.S)
            for index, code in enumerate(blocks):
                if "struct CounterView: View" in code and "@State private var count" in code:
                    cases.append(
                        {
                            "cell_id": cell,
                            "block": index,
                            "kind": "core_counter",
                            "source": "import SwiftUI\n" + code,
                            "adaptation": "Only import SwiftUI prepended; exact answer block otherwise.",
                        }
                    )
                if cell == "cell-010" and "struct CardView: View" in code:
                    cases.append(
                        {
                            "cell_id": cell,
                            "block": index,
                            "kind": "opaque_content_property",
                            "source": "import SwiftUI\n" + code,
                            "adaptation": "Only import SwiftUI prepended; exact answer block otherwise.",
                        }
                    )
    cases.append(
        {
            "cell_id": "cell-012",
            "block": 7,
            "kind": "list_onDelete_placement",
            "source": r"""import SwiftUI
struct CheckList: View {
    @State private var items = ["A", "B"]
    var body: some View {
        List(items, id: \.self) { item in Text(item) }
            .onDelete { indexSet in items.remove(atOffsets: indexSet) }
    }
}
""",
            "adaptation": "Investigative reconstruction, not verbatim answer: replace ellipsis with Text row, supply state/type/id and wrapper; retain .onDelete directly on List. This tests modifier placement only.",
        }
    )
    cases.append(
        {
            "cell_id": "cell-012",
            "block": 7,
            "kind": "onDelete_reference_placement",
            "source": r"""import SwiftUI
struct CheckList: View {
    @State private var items = ["A", "B"]
    var body: some View {
        List {
            ForEach(items, id: \.self) { item in Text(item) }
                .onDelete { indexSet in items.remove(atOffsets: indexSet) }
        }
    }
}
""",
            "adaptation": "Same investigative wrapper, .onDelete on ForEach as in the archived retrieved List example; not substituted into historical output.",
        }
    )
    with tempfile.TemporaryDirectory(prefix="pe6203-swift-types-") as tmp:
        for case in cases:
            path = Path(tmp) / "Example.swift"
            path.write_text(case["source"])
            run = subprocess.run(
                [
                    "/usr/bin/swiftc",
                    "-typecheck",
                    "-module-cache-path",
                    str(Path(tmp) / "cache"),
                    str(path),
                ],
                text=True,
                capture_output=True,
                timeout=60,
            )
            case.update(
                {
                    "source_sha256": hashlib.sha256(case["source"].encode()).hexdigest(),
                    "exit_code": run.returncode,
                    "diagnostic": run.stderr.replace(tmp, "<temporary>"),
                }
            )
    print(
        json.dumps(
            {
                "new_model_calls": 0,
                "generated_code_executed": False,
                "compiler": "Apple Swift 6.3.3 on macOS 26.5.2, installed host SDK",
                "scope": "Selected fragments only, host type checking; no iOS runtime or complete app validation.",
                "cases": cases,
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
