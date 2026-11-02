"""Materialize public, symmetric build support; never copies native memories or task answers."""
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parent


def main():
    evidence = ROOT / "results/evidence/program-memory-runtime-20261101"
    fixture = BASE / "common-input"
    runtime = ROOT / ".cache/program-memory-runtime-v1"
    records = json.loads((evidence / "registry-manifest.json").read_text())["records"]
    assert len(records) == 23 and all("sha256" in x for x in records)
    theme, frames = {}, {}
    for row in records:
        source = evidence / "registry" / (row["name"]+".json")
        assert hashlib.sha256(source.read_bytes()).hexdigest() == row["sha256"]
        for key, value in row["cssVars"].get("theme", {}).items():
            assert key not in theme or theme[key] == value
            theme[key] = value
        for key, value in row["css"].items():
            assert key not in frames or frames[key] == value
            frames[key] = value
    css = '@import "tailwindcss" source(none);\n@source "./src";\n@source "./public/index.html";\n@theme {\n'
    css += ''.join(f'  --{key}: {value};\n' for key,value in sorted(theme.items()))+'}\n'
    for name, steps in sorted(frames.items()):
        css += name+' {\n'
        for percent, properties in steps.items():
            css += '  '+percent+' {'+' '.join(f'{k}: {v};' for k,v in properties.items())+'}\n'
        css += '}\n'
    (fixture / "styles.css").write_text(css)
    button_source = json.loads((evidence / "registry/button.json").read_text())
    button = next(x for x in button_source["files"] if x["path"].endswith('button.tsx'))
    p = fixture / "src/components/ui/button.tsx"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(button["content"])
    (fixture / "runtime.json").write_text(json.dumps({"dependency_root": str(runtime), "node": str(ROOT / ".cache/node-runtime/node_modules/node/bin/node")}, indent=2)+"\n")
    for name in ("package.json", "package-lock.json"):
        shutil.copyfile(runtime / name, fixture / name)
    (evidence / "common-source-map.json").write_text(json.dumps({
        "animation_names": sorted(theme), "keyframes": sorted(frames),
        "button": "Official shadcn new-york registry common primitive, not a MagicUI memory.",
        "no_component_source_no_oracle": True,
        "files": {str(p.relative_to(fixture)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(fixture.rglob('*')) if p.is_file()},
    }, indent=2)+"\n")


if __name__ == "__main__":
    main()
