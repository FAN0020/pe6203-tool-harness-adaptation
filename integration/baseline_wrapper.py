"""Temporary integration wrapper for the baseline adaptation interface.

The wrapper isolates the baseline implementation from Group A's unfinished
runner and metadata format. It can use synthetic fixtures now and receive a
real input loader later.
"""

from __future__ import annotations

import json
import math
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

Strategy = str
AdaptFunction = Callable[
    [Mapping[str, Any], Mapping[str, Any], Strategy, Any],
    tuple[Any, Any, Mapping[str, Any]],
]
InputLoader = Callable[[], tuple[Mapping[str, Any], Mapping[str, Any]]]


REQUIRED_COST_FIELDS = {
    "model_calls",
    "input_tokens",
    "output_tokens",
    "api_cost_usd",
    "elapsed_seconds",
    "update_operations",
}

SUPPORTED_STRATEGIES = {"no_update", "full_rewrite"}


def normalize_metadata(raw_metadata: Mapping[str, Any]) -> Mapping[str, Any]:
    """Normalize metadata before calling ``adapt``.

    This is intentionally a pass-through for the temporary synthetic format.
    Replace this function after Group A confirms the real metadata schema.
    """
    return raw_metadata


def validate_adapt_result(result: Any) -> tuple[Any, Any, Mapping[str, Any]]:
    """Validate the shared adapt return contract."""
    if not isinstance(result, tuple) or len(result) != 3:
        raise TypeError("adapt(...) must return (new_knowledge, diff_log, update_cost)")

    new_knowledge, diff_log, update_cost = result

    if not isinstance(update_cost, Mapping):
        raise TypeError("update_cost must be a mapping")

    missing_fields = REQUIRED_COST_FIELDS - set(update_cost.keys())
    if missing_fields:
        raise ValueError(f"update_cost is missing required fields: {sorted(missing_fields)}")

    for field in REQUIRED_COST_FIELDS:
        value = update_cost[field]
        if value is None and field in {"input_tokens", "output_tokens", "api_cost_usd"}:
            continue
        if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
            raise ValueError(f"update_cost[{field!r}] must be a non-negative number")

    return new_knowledge, diff_log, update_cost


def run_baseline_once(
    adapt_fn: AdaptFunction,
    old_knowledge: Mapping[str, Any],
    raw_new_metadata: Mapping[str, Any],
    strategy: Strategy,
    context: Any = None,
) -> dict[str, Any]:
    """Run one baseline update using either synthetic or real inputs.

    ``adapt_fn`` is injected rather than imported so this wrapper can be used
    before the teammate's module path is finalized.
    """
    if strategy not in SUPPORTED_STRATEGIES:
        raise ValueError(
            f"Unsupported strategy {strategy!r}; expected one of {sorted(SUPPORTED_STRATEGIES)}"
        )

    new_metadata = normalize_metadata(raw_new_metadata)
    result = adapt_fn(
        old_knowledge=old_knowledge,
        new_metadata=new_metadata,
        strategy=strategy,
        context=context,
    )
    new_knowledge, diff_log, update_cost = validate_adapt_result(result)

    return {
        "strategy": strategy,
        "new_knowledge": new_knowledge,
        "diff_log": diff_log,
        "update_cost": dict(update_cost),
        "metadata_version": new_metadata.get("version"),
    }


def run_baseline_from_loader(
    adapt_fn: AdaptFunction,
    input_loader: InputLoader,
    strategy: Strategy,
    context: Any = None,
) -> dict[str, Any]:
    """Run a baseline after obtaining inputs from a fixture or real adapter.

    The current fixture loader and the future Group A loader must both return:

    ``(old_knowledge, raw_new_metadata)``
    """
    old_knowledge, raw_new_metadata = input_loader()
    return run_baseline_once(
        adapt_fn=adapt_fn,
        old_knowledge=old_knowledge,
        raw_new_metadata=raw_new_metadata,
        strategy=strategy,
        context=context,
    )


def save_run_record(record: Mapping[str, Any], output_path: str | Path) -> None:
    """Save the update-stage result for later review."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(record, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def fixture_input_loader(
    old_knowledge: Mapping[str, Any],
    new_metadata: Mapping[str, Any],
) -> InputLoader:
    """Create an input loader for a synthetic fixture."""

    def load() -> tuple[Mapping[str, Any], Mapping[str, Any]]:
        return old_knowledge, new_metadata

    return load


# After Group A confirms the real interface, replace the fixture loader with
# an adapter-specific loader that returns:
#
#     old_knowledge, raw_new_metadata = load_real_inputs_from_a(...)
#
# The call to run_baseline_from_loader(...) can remain unchanged.
