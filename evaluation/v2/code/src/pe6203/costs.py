"""Provider-reported USD only; never replace unknown billing with zero."""

import math
from collections.abc import Mapping
from decimal import Decimal


def valid_usd(value):
    """Accept finite, nonnegative JSON numbers, including a real zero."""
    if type(value) not in (int, float) or value < 0:
        return None
    try:
        return value if math.isfinite(value) else None
    except OverflowError:
        return None


def provider_usd(usage):
    """OpenRouter reports request cost in usage.cost; other providers may omit it."""
    return valid_usd(usage.get("cost")) if isinstance(usage, Mapping) else None


def sum_usd(values):
    """Return a complete sum, or None if any constituent charge is unknown."""
    values = list(values)
    if not values or any(valid_usd(value) is None for value in values):
        return None
    # Decimal string conversion avoids accumulating binary rounding artifacts.
    total = float(sum((Decimal(str(value)) for value in values), Decimal(0)))
    return valid_usd(total)
