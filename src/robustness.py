"""Retry with backoff, screenshot-on-failure, and timeout utilities."""

import asyncio
import random
from collections.abc import Awaitable, Callable
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any, TypeVar

from playwright.async_api import Page

from config.settings import settings

T = TypeVar("T")


async def retry_with_backoff(
    func: Callable[[], Awaitable[T]],
    max_retries: int | None = None,
    base_delay: float | None = None,
    max_delay: float | None = None,
    retryable_exceptions: tuple[type[Exception], ...] = (Exception,),
    on_retry: Callable[[int, Exception, float], None] | None = None,
) -> T:
    """Execute func with exponential backoff + random jitter.

    Base delay doubles each retry up to max_delay. Returns the first
    successful result, or raises the last exception after exhausting retries.
    """
    mr = max_retries if max_retries is not None else settings.max_retries
    bd = base_delay if base_delay is not None else settings.retry_base_delay_s
    md = max_delay if max_delay is not None else settings.retry_max_delay_s
    last_exc: Exception | None = None

    for attempt in range(mr + 1):
        try:
            return await func()
        except retryable_exceptions as e:
            last_exc = e
            if attempt == mr:
                raise
            delay = min(bd * (2**attempt), md)
            delay *= 1 + random.random() * 0.5  # jitter
            if on_retry:
                on_retry(attempt + 1, e, delay)
            await asyncio.sleep(delay)

    raise last_exc  # type: ignore[redundant-exc]


def screenshot_on_failure(page_getter: Callable[[], Page]):
    """Decorator: take a screenshot if the wrapped function raises."""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception:
                page = page_getter()
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                path: Path = settings.screenshot_dir / f"FAIL_{func.__name__}_{ts}.png"
                try:
                    await page.screenshot(path=str(path))
                except Exception:
                    pass  # best-effort
                raise

        return wrapper

    return decorator


async def wait_for_condition(
    page: Page,
    condition_fn: Callable[[], Awaitable[Any]],
    timeout: float = 15,
    interval: float = 0.5,
) -> Any:
    """Poll condition_fn every `interval` seconds until truthy or timeout."""
    import asyncio
    deadline = asyncio.get_event_loop().time() + timeout
    while True:
        result = await condition_fn()
        if result:
            return result
        if deadline is not None and asyncio.get_event_loop().time() + interval > deadline:
            return None
        await asyncio.sleep(interval)
        if deadline is not None and asyncio.get_event_loop().time() > deadline:
            return None