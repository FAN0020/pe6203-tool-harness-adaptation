"""Bounded native media facts; no task content or generic execution instructions."""

RULES = {
    "@hugeicons/mcp-server::search_icons": "Verified Middle/Late style-filter defect: the native "
    "search helper returns only id, name, tags, category, "
    "featured and version. The added style filter reads "
    "absent style/variant/stroke fields and can discard "
    "real matching icons. Omit style when discovering "
    "names; a style-filtered empty result is not evidence "
    "that matching icons do not exist. If a particular "
    "style is required, use a returned name with "
    "get_icon_glyph_by_style to check that style.",
    "@hugeicons/mcp-server::get_icon_glyph_by_style": "Verified native alternative to the "
    "changed search style filter: this "
    "existing tool accepts icon_name and style "
    "and can return a primary glyph containing "
    "the matching icon_name, style and "
    "unicode. It checks a known name and "
    "style, not search relevance. A glyph "
    "record is not an SVG download or a "
    "browser-rendered preview; describe only "
    "the artifact actually returned.",
    "plantuml-mcp-server::generate_plantuml_diagram": "Verified Late regression: supplying "
    "output_path fails with response is not "
    "defined because the fetched response is "
    "out of scope in the save branch. Changing "
    "the filename does not repair that branch. "
    "Omitting output_path with default "
    "validation and fetch checks succeeds and "
    "returns the generated image URL/markdown "
    "embed; this is a verified path for a "
    "requested diagram without a local-file "
    "requirement. Deliver that returned image "
    "reference without claiming a local file "
    "was saved. If a local file is explicitly "
    "required, URL generation alone does not "
    "fulfill it; report the unresolved local "
    "save instead of asserting success.",
}

ICON_FACTS = {
    "default_count": 66,
    "kind": "icon_style_contract_v1",
    "native_glyph_by_style_success": True,
    "projected_style_fields": False,
    "style_count": 0,
}

DIAGRAM_FACTS = {
    "kind": "plantuml_delivery_contract_v1",
    "save_error": "response is not defined",
    "url_matches_rendered_early_middle": True,
    "url_without_output_path_success": True,
}


def native_media_notes(observation):
    identity = (observation["server"], observation["tool"])
    if identity == ("@hugeicons/mcp-server", "search_icons"):
        valid = observation["stage"] in ("middle", "late")
        expected = ICON_FACTS
        keys = [
            "@hugeicons/mcp-server::search_icons",
            "@hugeicons/mcp-server::get_icon_glyph_by_style",
        ]
    elif identity == ("plantuml-mcp-server", "generate_plantuml_diagram"):
        valid = observation["stage"] == "late"
        expected = DIAGRAM_FACTS
        keys = ["plantuml-mcp-server::generate_plantuml_diagram"]
    else:
        raise ValueError("Invalid native media contract source")
    if not valid or observation["result"] != expected:
        raise ValueError("Invalid verified native media contract evidence")
    return {key: RULES[key] for key in keys}
