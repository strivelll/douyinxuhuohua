"""Page navigation: home, popups, private-message panel, and back-to-panel."""

import asyncio
import logging
import random

from playwright.async_api import Page

from config.settings import settings
logger = logging.getLogger(__name__)

from src.robustness import wait_for_condition
from src.selectors import POPUP_EVALUATE_JS, WAIT_NAMES_JS, locate_panel, locate_sixin


async def load_home(page: Page) -> None:
    """Navigate to Douyin homepage and wait for DOM ready."""
    await page.goto(settings.home_url, wait_until="domcontentloaded", timeout=settings.home_timeout_ms)
    for _ in range(15):
        if await page.evaluate("() => document.readyState === 'complete'"):
            break
        await asyncio.sleep(1)


async def _dismiss_one_popup(page: Page) -> bool:
    """Try to dismiss one popup. Returns True if something was clicked."""
    pos = await page.evaluate(POPUP_EVALUATE_JS)
    if not pos:
        return False
    await page.mouse.click(pos["cx"], pos["cy"])
    await asyncio.sleep(random.uniform(0.5, 1.5))
    return True


async def dismiss_all_popups(page: Page, max_iterations: int = 8) -> int:
    """Dismiss all visible popups in a loop. Returns count dismissed."""
    count = 0
    for _ in range(max_iterations):
        if not await _dismiss_one_popup(page):
            break
        count += 1
    return count


async def hover_sixin(page: Page) -> bool:
    """Find and hover the 私信 trigger to open the conversation panel.

    Returns True if panel appears within the timeout.
    """
    pos = await locate_sixin(page)
    if not pos:
        return False
    logger.info("找到私信位置: cx=%d, cy=%d", pos.get("cx", -1), pos.get("cy", -1))
    await page.mouse.move(pos["cx"], pos["cy"], steps=10)
    await asyncio.sleep(3.5)
    return True


async def open_panel(page: Page) -> bool:
    """Open the conversation panel. Try hover first, fallback to direct URL."""
    if await hover_sixin(page):
        panel = await wait_for_condition(
            page, lambda: locate_panel(page), timeout=settings.panel_wait_seconds
        )
        if panel:
            return True
    # Fallback: try direct navigation
    try:
        await page.goto("https://www.douyin.com/messages/", wait_until="domcontentloaded", timeout=10000)
        panel = await wait_for_condition(
            page, lambda: locate_panel(page), timeout=5
        )
        return panel is not None
    except Exception:
        return False


async def wait_names_load(page: Page) -> list[str]:
    """Wait for contact names to load (not numeric IDs)."""
    names = await wait_for_condition(
        page,
        lambda: page.evaluate(WAIT_NAMES_JS),
        timeout=settings.panel_wait_seconds,
        interval=1,
    )
    return names or []


async def back_to_panel(page: Page) -> None:
    """Collapse the chat window and re-open the contact panel."""
    await page.mouse.click(500, 100)
    await asyncio.sleep(random.uniform(1, 2))
    await open_panel(page)
    await wait_names_load(page)