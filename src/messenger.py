"""Message sending with confirmation."""

import asyncio
import random

from playwright.async_api import Page

from config.settings import settings
from src.contacts import ContactInfo
from src.selectors import CONFIRM_SENT_JS, FIND_CONTACT_JS, FIND_INPUT_JS


async def click_contact(page: Page, name: str) -> bool:
    """Find and click a conversation item by name."""
    return await page.evaluate(FIND_CONTACT_JS, name) or False


async def locate_input_selector(page: Page) -> str | None:
    """Find the chat input field selector."""
    return await page.evaluate(FIND_INPUT_JS) or None


async def confirm_sent(page: Page, expected_text: str) -> bool:
    """Check if the last message matches expected text."""
    await asyncio.sleep(1.5)
    return await page.evaluate(CONFIRM_SENT_JS, expected_text) or False


async def send_message_to_contact(
    page: Page, contact: ContactInfo, message: str
) -> tuple[bool, str | None]:
    """Send a message to one contact. Returns (success, error_message)."""
    name = contact.name

    if not await click_contact(page, name):
        return False, "找不到联系人条目"

    await asyncio.sleep(random.uniform(2, 3.5))

    input_sel = await locate_input_selector(page)
    if not input_sel:
        return False, "找不到输入框"

    inp = page.locator(input_sel).first
    await inp.click()
    await asyncio.sleep(random.uniform(0.5, 1))
    await inp.fill(message)
    await asyncio.sleep(random.uniform(0.5, 1.5))

    await page.keyboard.press("Enter")
    await asyncio.sleep(3)

    return True, None