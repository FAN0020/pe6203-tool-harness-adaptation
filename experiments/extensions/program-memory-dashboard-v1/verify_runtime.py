"""Test shared build support against archived native programs, outside agent inputs."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parent
EVIDENCE = ROOT / "results/evidence/program-memory-runtime-20261101"
NODE = ROOT / ".cache/node-runtime/node_modules/node/bin/node"


def main():
    label = sys.argv[1]
    output = EVIDENCE / label
    output.mkdir(exist_ok=False)
    common = BASE / "common-input"
    assert (common / "build.cjs").is_file(), "Shared build.cjs must exist before executable memory can be admitted"
    work = output / "workspace"
    shutil.copytree(common, work)
    (work / "home").mkdir()
    env = {"PATH": str(NODE.parent)+":/usr/bin:/bin", "HOME": str(work/"home"), "TMPDIR": str(work)}
    entries = []
    for file in ("magicui-argument-routing-probes-20261101/call-09.json", "magicui-artifact-dependencies-20261101/call-02.json"):
        data = json.loads((ROOT / "results/evidence" / file).read_text())
        entries.extend(x for b in data["result"]["content"] if b["type"] == "text" for x in json.loads(b["text"]))
    paths = []
    for x in entries:
        p = work / "src/native" / (x["name"]+".tsx")
        p.parent.mkdir(exist_ok=True, parents=True)
        p.write_text(x["content"])
        paths.append({"name": x["name"], "sha256": hashlib.sha256(p.read_bytes()).hexdigest()})
    main_file = work / "src/main.tsx"
    main_file.write_text('\n'.join(f'export * as component{i} from "./native/{x["name"]}";' for i,x in enumerate(entries)))
    def build(name):
        run = subprocess.run([str(NODE), "build.cjs"], cwd=work, env=env, capture_output=True, text=True, timeout=30)
        (output / (name+".stdout.txt")).write_text(run.stdout)
        (output / (name+".stderr.txt")).write_text(run.stderr)
        assert run.returncode == 0, f"{name}: {run.stderr[:1500]}"
    build("all23-compile")
    main_file.write_text('''import React from "react";
import {createRoot} from "react-dom/client";
import {AnimatedGradientText} from "./native/animated-gradient-text";
import {Meteors} from "./native/meteors";
const p=new URLSearchParams(location.search);
createRoot(document.getElementById("root")!).render(<main>
  <h1><AnimatedGradientText data-testid="gradient" colorFrom={p.get("from")||"#ff0000"} colorTo={p.get("to")||"#0000ff"}>Reusable memory canary</AnimatedGradientText></h1>
  <section data-testid="meteor-container" style={{position:"relative",height:320,overflow:"hidden",background:"#101727"}}><Meteors number={Number(p.get("count")??7)} minDelay={0} maxDelay={0} minDuration={2} maxDuration={2}/></section>
</main>);
''')
    (work / "public/index.html").write_text('<!doctype html><html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="styles.css"><div id="root"></div><script src="app.js"></script></html>')
    build("selected-render-build")
    (output / "native-code-manifest.json").write_text(json.dumps(paths, indent=2)+"\n")
    command = [str(NODE), str(BASE/"verify_runtime_browser.cjs"), str(work/"public"), str(output)]
    run = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=60)
    (output / "browser.stdout.txt").write_text(run.stdout)
    (output / "browser.stderr.txt").write_text(run.stderr)
    assert run.returncode == 0, run.stdout+run.stderr
    print(run.stdout)


if __name__ == "__main__":
    main()
