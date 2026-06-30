"""Browser lifecycle: launch persistent context with anti-detection."""

from pathlib import Path

from playwright.async_api import BrowserContext, Playwright

from config.settings import settings

BROWSER_ARGS = settings.browser_args + [
    f"--window-size={settings.viewport_width},{settings.viewport_height}",
]

ANTI_DETECT_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh'] });
"""


def cleanup_locks(profile_dir: Path | None = None) -> None:
    """Delete Chromium singleton lock files to prevent 'profile in use' errors."""
    target = profile_dir or settings.profile_dir
    for name in ["SingletonLock", "SingletonSocket", "SingletonCookie"]:
        (target / name).unlink(missing_ok=True)


async def create_context(pw: Playwright) -> BrowserContext:
    """Launch persistent Chromium context with anti-detection measures."""
    ctx = await pw.chromium.launch_persistent_context(
        user_data_dir=str(settings.profile_dir),
        headless=False,
        args=BROWSER_ARGS,
        viewport={"width": settings.viewport_width, "height": settings.viewport_height},
        user_agent=settings.user_agent,
        locale=settings.locale,
        timezone_id=settings.timezone,
    )
    await ctx.add_init_script(ANTI_DETECT_SCRIPT)
    return ctx