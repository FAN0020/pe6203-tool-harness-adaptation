"""Optional shared per-request reservation ledger for bounded OpenRouter studies."""

import fcntl
import hashlib
import json
from contextlib import contextmanager
from copy import deepcopy
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from .costs import provider_usd


class BudgetStopped(RuntimeError):
    pass


@contextmanager
def ledger(policy):
    path = Path(policy["ledger"])
    path.parent.mkdir(parents=True, exist_ok=True)
    identity = {k: v for k, v in policy.items() if k != "ledger"}
    with path.with_suffix(".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        data = (
            json.loads(path.read_text())
            if path.exists()
            else {
                "policy": identity,
                "known_usd": "0",
                "unknown_reserved_usd": "0",
                "blocked": False,
                "requests": [],
            }
        )
        if data["policy"] != identity:
            raise BudgetStopped("Budget policy changed; ledger cannot be reset")
        try:
            yield data
        finally:
            temporary = path.with_suffix(".tmp")
            temporary.write_text(json.dumps(data, indent=2) + "\n")
            temporary.replace(path)


def reserve(client, policy, kwargs):
    if client.max_retries != 0:
        raise BudgetStopped("SDK retries must be disabled; reserve each explicit attempt")
    if str(client.base_url) != "https://openrouter.ai/api/v1/":
        raise BudgetStopped("Spend guard requires the priced OpenRouter endpoint")
    if kwargs.get("model") != policy["model"] or kwargs.get("n", 1) != 1:
        raise BudgetStopped("Unpriced model or multiple completions")
    if kwargs.get("stream") or kwargs.get("plugins") or kwargs.get("models"):
        raise BudgetStopped("Unpriced streaming, plugins or fallback models")
    maximum = kwargs.get("max_completion_tokens", kwargs.get("max_tokens"))
    if type(maximum) is not int or not 0 < maximum <= policy["max_completion_tokens"]:
        raise BudgetStopped("Missing or oversized completion bound")
    if type(policy["context_tokens"]) is not int or policy["context_tokens"] < maximum:
        raise BudgetStopped("Invalid model context bound")
    rates = [Decimal(policy[k]) for k in ("prompt_per_million", "completion_per_million")]
    limit = Decimal(policy["limit_usd"])
    if any(not v.is_finite() or v < 0 for v in rates) or not limit.is_finite() or limit <= 0:
        raise BudgetStopped("Invalid finite price/limit")
    request = deepcopy(kwargs)
    extra = request.setdefault("extra_body", {})
    if set(extra) - {"reasoning", "response_format", "provider"}:
        raise BudgetStopped("Unpriced extra request options")
    route = policy.get("provider_route", {})
    supplied_route = {k: v for k, v in extra.get("provider", {}).items() if k != "max_price"}
    if supplied_route and supplied_route != route:
        raise BudgetStopped("Unexpected provider override")
    extra["provider"] = {
        **deepcopy(route),
        "max_price": {"prompt": float(rates[0]), "completion": float(rates[1]), "request": 0},
    }
    # Full published context is a conservative input bound; output is additionally reserved.
    bound = (policy["context_tokens"] * rates[0] + maximum * rates[1]) / Decimal(1000000)
    with ledger(policy) as data:
        if data["blocked"] or any(r["status"] == "pending" for r in data["requests"]):
            raise BudgetStopped("Unsettled/unknown charge or previous budget stop")
        if Decimal(data["known_usd"]) + Decimal(data["unknown_reserved_usd"]) + bound > limit:
            data.update(blocked=True, stop_reason="insufficient_worst_case_reserve")
            raise BudgetStopped("Insufficient funds for worst-case request; no request sent")
        index = len(data["requests"])
        data["requests"].append(
            {
                "status": "pending",
                "started_at": datetime.now(UTC).isoformat(),
                "model": request["model"],
                "max_completion_tokens": maximum,
                "request_sha256": hashlib.sha256(
                    json.dumps(request, sort_keys=True).encode()
                ).hexdigest(),
                "provider": extra["provider"],
                "reserved_usd": str(bound),
                "actual_usd": None,
            }
        )
    return index, request


def settle(policy, index, response=None, error=None):
    usage = response.usage.model_dump() if response is not None and response.usage else None
    cost = provider_usd(usage)
    with ledger(policy) as data:
        row = data["requests"][index]
        if row["status"] != "pending":
            raise BudgetStopped("Request was already settled")
        row.update(finished_at=datetime.now(UTC).isoformat(), error_type=error)
        if response is not None and policy.get("expected_provider"):
            row.update(
                actual_provider=getattr(response, "provider", None),
                actual_model=response.model,
                response_id=response.id,
            )
            if (
                row["actual_provider"] != policy["expected_provider"]
                or row["actual_model"] != policy["model"]
            ):
                data.update(blocked=True, stop_reason="unexpected_provider_or_model")
        if cost is None:
            row["status"] = "unknown_charge"
            data["unknown_reserved_usd"] = str(
                Decimal(data["unknown_reserved_usd"]) + Decimal(row["reserved_usd"])
            )
            data.update(blocked=True, stop_reason="unknown_charge")
        else:
            actual = Decimal(str(cost))
            row.update(status="settled", actual_usd=str(actual))
            data["known_usd"] = str(Decimal(data["known_usd"]) + actual)
            if actual > Decimal(row["reserved_usd"]):
                data.update(blocked=True, stop_reason="provider_exceeded_declared_price_bound")


def stopped(policy):
    if not policy or not Path(policy["ledger"]).exists():
        return False
    data = json.loads(Path(policy["ledger"]).read_text())
    return data["blocked"] or any(r["status"] == "pending" for r in data["requests"])


def complete_sync(client, policy, **kwargs):
    if not policy:
        return client.chat.completions.create(**kwargs)
    index, request = reserve(client, policy, kwargs)
    try:
        response = client.chat.completions.create(**request)
    except BaseException as exc:
        settle(policy, index, error=type(exc).__name__)
        raise
    settle(policy, index, response)
    return response


async def complete_async(client, policy, **kwargs):
    if not policy:
        return await client.chat.completions.create(**kwargs)
    index, request = reserve(client, policy, kwargs)
    try:
        response = await client.chat.completions.create(**request)
    except BaseException as exc:
        settle(policy, index, error=type(exc).__name__)
        raise
    settle(policy, index, response)
    return response
