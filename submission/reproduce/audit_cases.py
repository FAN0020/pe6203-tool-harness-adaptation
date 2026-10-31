"""Build traceable candidate records from the existing local corpus; no requests."""

import json
from collections import Counter

from screen_trajectories import FIELDS, OUT, ROOT, canonical, read, records, screen


def details(path):
    row = screen(path)
    d = path.parent
    old_path = next(
        (
            p / "catalogs" / str(row["task"]) / "early.json"
            for p in d.parents
            if (p / "catalogs" / str(row["task"]) / "early.json").exists()
        ),
        None,
    )
    old, target, updated = (
        records(read(old_path)),
        records(read(d / "environment-metadata.json")),
        records(read(d / "knowledge.json")),
    )
    diffs = []
    for tid in sorted(set(old) | set(target) | set(updated)):
        for field in FIELDS + ["usage_rules"]:
            before, current, after = (x.get(tid, {}).get(field) for x in [old, target, updated])
            if before != after or before != current:
                diffs.append(
                    {
                        "tool_id": tid,
                        "field": field,
                        "original": before,
                        "target": current,
                        "updated": after,
                        "metadata_unchanged_tool": canonical(old.get(tid))
                        == canonical(target.get(tid)),
                    }
                )
    trace = read(path)
    calls = [
        {"round": e.get("round"), "call": e["call"], "observation": e["result"]}
        for e in trace.get("events", [])
        if e.get("type") == "tool_result"
    ]
    row.update(
        original_knowledge_path=str(old_path.relative_to(ROOT)) if old_path else None,
        updated_knowledge_path=str((d / "knowledge.json").relative_to(ROOT)),
        exact_differences=diffs,
        calls_and_observations=calls,
        classification="inconclusive",
        classified_claim="The observed behavior is caused by under/over-updating harness knowledge",
        causal_limit="Structural screening signals do not establish that an edited or stale record caused a regression. No isolated counterfactual was run.",
    )
    # Direct parameter-level rejection is demonstrable, but only for No Update.
    stale = []
    for call in calls:
        f = call["call"]["function"]
        if "validate_syntax" in f["name"] and call["observation"].get("isError"):
            args = json.loads(f["arguments"])
            if "allow_variables" not in args and "allow_variables" in json.dumps(
                call["observation"]
            ):
                stale.append(call)
    if row["method"] == "no_update" and stale:
        row.update(
            classification="confirmed",
            classified_claim="Stale No Update schema caused calls without required allow_variables to be rejected",
            causal_limit="Confirms this local call failure mechanism, not an effect size on final TF and not a Selective Patch under-update failure.",
            directly_attributed_calls=stale,
        )
    if "finalized-trial-20261031/cells/task235-late-full_rewrite-r0/" in str(path):
        row.update(
            classification="suggestive",
            classified_claim="Unrelated Full Rewrite descriptions may contribute to redundant maps and missing units",
            causal_limit="Full Rewrite, not Selective Patch. Six later rollback/rewrite trajectories all scored 10/10, so causal damage remains unestablished.",
        )
    if "selective-search-v1.1-development-20261031/cells/task133-middle-linked_notes-r0/" in str(
        path
    ):
        row.update(
            classification="suggestive",
            classified_claim="Adding a note to metadata-unchanged evaluate may contribute to extra evaluation calls",
            causal_limit="Original Selective Patch had PE10 and 3 calls; linked_notes had PE5 and 6 calls. Four records differ between arms, including three changed records. The added note is about a semantically related validator, so metadata-unchanged does not prove unrelated. No isolated rollback or common provider seed.",
        )
    return row


def main():
    folder = OUT / "case-details"
    folder.mkdir(parents=True, exist_ok=True)
    candidates = []
    for path in sorted((ROOT / "results").rglob("raw_trace.json")):
        row = screen(path)
        if row["metadata_mismatches_vs_changed_target"] or row["modified_metadata_unchanged_tools"]:
            item = details(path)
            name = item["sha256"][:16] + ".json"
            (folder / name).write_text(json.dumps(item, ensure_ascii=False, indent=2) + "\n")
            candidates.append(
                {
                    k: item[k]
                    for k in [
                        "trace",
                        "sha256",
                        "task",
                        "stage",
                        "method",
                        "TF",
                        "PE",
                        "execution_status",
                        "classification",
                        "classified_claim",
                        "causal_limit",
                    ]
                }
                | {"evidence": "case-details/" + name}
            )
    studies = [
        (
            "U1",
            "confirmed",
            "Stale No Update parameter failure",
            "course-v1.3-final-20261031",
            "task133-late-no_update-r0",
            "Early validate_syntax requires only expression; Late adds mandatory allow_variables. Four initial calls omit it and are rejected. Later calls use tool-error feedback to recover. Final TF9.8/PE7.2, 38 calls. This confirms stale-knowledge call failures, not Selective Patch under-update.",
        ),
        (
            "U2",
            "contradicted",
            "Claim that the main Selective Patch missed allow_variables",
            "course-v1.3-final-20261031",
            "task133-late-selective_patch-r0",
            "Updated schema includes allow_variables and all three validation calls provide it. Four total calls, zero tool errors, TF10/PE7. The proposed parameter-omission attribution is contradicted.",
        ),
        (
            "O1",
            "suggestive",
            "Unrelated Full Rewrite regression",
            "finalized-trial-20261031",
            "task235-late-full_rewrite-r0",
            "All 28 chart records are unchanged across environments, but every description is regenerated. Five map calls and missing map-unit metadata accompany TF8.8/PE4.2. The rewrite explicitly mentions dataValueUnit, so omission is not proof of missing guidance. Cause unconfirmed; this is not original Selective Patch.",
        ),
        (
            "O2",
            "suggestive",
            "Related-note scope expansion",
            "selective-search-v1.1-development-20261031",
            "task133-middle-linked_notes-r0",
            "An added rule on unchanged evaluate is followed by three evaluate calls after two syntax checks. Original Selective Patch: PE10, 3 calls; linked_notes: PE5, 6 calls, TF10. Four rule records differ overall. Scope expansion and regression coincide, but causality and whether the knowledge is unrelated are unproven.",
        ),
        (
            "B1",
            "contradicted",
            "Claim that patch updates caused an Early truncation",
            "course-v1.3-final-20261031",
            "task133-early-selective_patch-r0",
            "All three Early arms use identical K0. Selective Patch truncates in round2 at the 4096 output limit; TF9/PE10. No patch had been applied, so attribution to changed harness knowledge is contradicted.",
        ),
        (
            "P1",
            "confirmed",
            "Upstream missing method is a tool execution failure",
            "course-v1.3-final-20261031",
            "task283-late-selective_patch-r0",
            "review_workspace_health(includeMemories=true) reports missing listMemories. The target metadata is correctly incorporated. The same run has an API retry, two empty-argument create_task errors and max_rounds. Only the missing-method observation is confirmed; its contribution to the terminal outcome is not isolated.",
        ),
        (
            "R1",
            "contradicted",
            "Claim that redundant map calls require Full Rewrite",
            "course-v1.3-final-20261031",
            "task235-middle-no_update-r0",
            "Five map calls occur with unchanged Early knowledge; TF10/PE4.8. This contradicts an exclusive rewrite explanation, not the possibility that some rewrites can be harmful.",
        ),
        (
            "J1",
            "inconclusive",
            "Judge rationale versus useful distinct checks",
            "selective-search-v3-development-20261031",
            "task133-middle-budget_feedback-r0",
            "TF10/PE5.2 with six calls and a completed answer. Some rationale labels distinct expressions and validation/evaluation as redundant. Whether these checks are unnecessary is partly subjective; do not silently replace official ratings.",
        ),
    ]
    case_studies = []
    for sid, classification, claim, cohort, cell, narrative in studies:
        p = ROOT / "results/raw" / cohort / "cells" / cell / "run/raw_trace.json"
        d = details(p)
        d.update(
            case_id=sid, classification=classification, classified_claim=claim, review=narrative
        )
        name = sid + ".json"
        (folder / name).write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n")
        case_studies.append(
            {
                "id": sid,
                "classification": classification,
                "claim": claim,
                "review": narrative,
                "evidence": "case-details/" + name,
            }
        )
    diagnostic = []
    for p in sorted(
        (ROOT / "results/raw/course-v1.3-retention-diagnostic-20261031").rglob("raw_trace.json")
    ):
        t = read(p)
        r = read(p.parent / "result.json")
        diagnostic.append(
            {
                "trace": str(p.relative_to(ROOT)),
                "TF": r["TF"],
                "PE": r["PE"],
                "annual_total_24_4_claim": "24.4" in t["answer"],
                "status": r["execution_status"],
            }
        )
    case_studies.append(
        {
            "id": "O3",
            "classification": "inconclusive",
            "claim": "Unrelated descriptions caused the historical chart regression",
            "review": "All six archived rewrite/description-rollback executions completed with TF/PE10. This negative result does not support causal damage and does not prove absence of rare harm. Three answers nevertheless claim an incorrect 24.4M annual total (correct sum25.4M), across both arms. Original scores remain unchanged.",
            "evidence": "diagnostic-review.json",
        }
    )
    (OUT / "diagnostic-review.json").write_text(
        json.dumps(
            {
                "classification": "inconclusive",
                "correct_monthly_sum_million": 25.4,
                "rows": diagnostic,
            },
            indent=2,
        )
        + "\n"
    )
    result = {
        "candidate_count": len(candidates),
        "candidate_classification_counts": dict(Counter(c["classification"] for c in candidates)),
        "classification_meaning": {
            "confirmed": "The specific stated mechanism is supported directly; not a general strategy effect.",
            "suggestive": "A plausible mechanism and regression coexist; confounding remains.",
            "inconclusive": "Evidence does not determine the causal claim.",
            "contradicted": "The stated attribution conflicts with the stored knowledge or calls.",
        },
        "candidates": candidates,
        "case_studies": case_studies,
        "requirement_status": "No confirmed natural original-Selective-Patch under-update or over-update trajectory. Stale No Update is separate. The linked-note case is a candidate variant, not the developed main method. Six negative diagnostics preserved.",
    }
    (OUT / "failure-cases.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(
        json.dumps(
            {
                "candidates": len(candidates),
                "classification": result["candidate_classification_counts"],
                "deep_case_studies": len(case_studies),
            }
        )
    )


if __name__ == "__main__":
    main()
