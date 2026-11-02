"""Compare complete Slides PPTX exports; permit content changes on slide 4 only.

Google's Office exporter regenerates table-style GUIDs. Resolve each reference
to its actual style definition before comparing; do not ignore formatting.
"""

import argparse
import hashlib
import json
import posixpath
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def styles(archive):
    result = {}
    for style in ET.fromstring(archive.read("ppt/tableStyles.xml")):
        identity = style.attrib.pop("styleId")
        result[identity] = sha(ET.tostring(style))
    return result


def normalized(data, definitions):
    tree = ET.fromstring(data)
    for node in tree.findall(".//a:tableStyleId", NS):
        node.text = definitions[node.text]
    return ET.tostring(tree)


def parts(archive):
    rels = {
        r.attrib["Id"]: r.attrib["Target"]
        for r in ET.fromstring(archive.read("ppt/_rels/presentation.xml.rels"))
    }
    result = []
    for node in ET.fromstring(archive.read("ppt/presentation.xml")).findall(".//p:sldId", NS):
        slide = posixpath.normpath("ppt/" + rels[node.attrib["{" + NS["r"] + "}id"]])
        relpath = posixpath.dirname(slide) + "/_rels/" + posixpath.basename(slide) + ".rels"
        notes = [
            r.attrib["Target"]
            for r in ET.fromstring(archive.read(relpath))
            if r.attrib["Type"].endswith("/notesSlide")
        ][0]
        result.append((slide, posixpath.normpath(posixpath.dirname(slide) + "/" + notes)))
    return result


def slide_images(archive, slide):
    relpath = posixpath.dirname(slide) + "/_rels/" + posixpath.basename(slide) + ".rels"
    return {
        r.attrib["Id"]: sha(
            archive.read(posixpath.normpath(posixpath.dirname(slide) + "/" + r.attrib["Target"]))
        )
        for r in ET.fromstring(archive.read(relpath))
        if r.attrib["Type"].endswith("/image")
    }


def compare(before, after):
    with zipfile.ZipFile(before) as a, zipfile.ZipFile(after) as b:
        pa, pb = parts(a), parts(b)
        sa, sb = styles(a), styles(b)
        changed_slides, changed_notes, changed_images = [], [], []
        for i, ((slide_a, note_a), (slide_b, note_b)) in enumerate(zip(pa, pb, strict=True), 1):
            if normalized(a.read(slide_a), sa) != normalized(b.read(slide_b), sb):
                changed_slides.append(i)
            if a.read(note_a) != b.read(note_b):
                changed_notes.append(i)
            if slide_images(a, slide_a) != slide_images(b, slide_b):
                changed_images.append(i)
        media_a = {p: sha(a.read(p)) for p in a.namelist() if p.startswith("ppt/media/")}
        media_b = {p: sha(b.read(p)) for p in b.namelist() if p.startswith("ppt/media/")}
        return {
            "slide_count_before": len(pa),
            "slide_count_after": len(pb),
            "changed_slides_including_formatting": changed_slides,
            "changed_notes": changed_notes,
            "media_payloads_unchanged": sorted(media_a.values()) == sorted(media_b.values()),
            "slides_with_changed_image_payloads": changed_images,
            "media_comparison": "resolve renumbered image files to payload hashes per slide",
            "table_style_comparison": "references resolved to exact definition hashes",
            "before_pptx_sha256": sha(Path(before).read_bytes()),
            "after_pptx_sha256": sha(Path(after).read_bytes()),
            "status": "passed"
            if changed_slides == changed_notes == [4]
            and len(pa) == len(pb)
            and sorted(media_a.values()) == sorted(media_b.values())
            and not changed_images
            else "failed",
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = compare(args.before, args.after)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
