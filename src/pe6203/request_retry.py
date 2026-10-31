"""Bounded retries of identical model requests, never tool calls or scored trajectories."""

import asyncio
import time
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

from openai import APIConnectionError, APIStatusError


def failure_details(exc):
    leaves = []

    def visit(error):
        if isinstance(error, BaseExceptionGroup):
            for child in error.exceptions:
                visit(child)
        else:
            leaves.append(error)

    visit(exc)
    transport = any(
        isinstance(e, APIConnectionError)
        or isinstance(e, APIStatusError)
        and (e.status_code == 429 or e.status_code >= 500)
        for e in leaves
    )
    return {
        "failure_category": "model_transport" if transport else "execution",
        "causes": [type(e).__name__ for e in leaves],
    }


def retry_event(exc, failed_attempt, policy):
    policy = policy or {}
    maximum = policy.get("max_retries", 0)
    delay = policy.get("backoff_seconds", 2)
    if (
        type(maximum) is not int
        or not 0 <= maximum <= 2
        or type(delay) not in (int, float)
        or not 0 <= delay <= 60
    ):
        raise ValueError("Retry policy requires max_retries 0–2 and backoff_seconds 0–60")
    status = getattr(exc, "status_code", None)
    transient = (
        isinstance(exc, APIConnectionError)
        or isinstance(exc, APIStatusError)
        and (status == 429 or status >= 500)
    )
    if not transient or failed_attempt > maximum:
        return None
    response = getattr(exc, "response", None)
    header = response.headers.get("retry-after") if response is not None else None
    if header:
        try:
            wait = float(header)
        except ValueError:
            try:
                wait = (parsedate_to_datetime(header) - datetime.now(UTC)).total_seconds()
            except (TypeError, ValueError):
                return None
        delay = max(delay, wait)
    if delay > 60:
        return None  # Do not retry earlier than the provider's requested delay.
    return {
        "error_type": type(exc).__name__,
        "http_status": status,
        "failed_attempt": failed_attempt,
        "retry_delay_seconds": delay,
        "usage": None,
    }


async def request_async(invoke, policy, on_retry):
    attempt = 0
    while True:
        try:
            return await invoke()
        except Exception as exc:
            attempt += 1
            event = retry_event(exc, attempt, policy)
            if event is None:
                raise
            on_retry(event)
            await asyncio.sleep(event["retry_delay_seconds"])


def request_sync(invoke, policy, on_retry):
    attempt = 0
    while True:
        try:
            return invoke()
        except Exception as exc:
            attempt += 1
            event = retry_event(exc, attempt, policy)
            if event is None:
                raise
            on_retry(event)
            time.sleep(event["retry_delay_seconds"])
