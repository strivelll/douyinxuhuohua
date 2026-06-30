"""Login state detection for Douyin."""

from enum import Enum

from playwright.async_api import Page


class AuthState(Enum):
    LOGGED_IN = "logged_in"
    NOT_LOGGED_IN = "not_logged_in"
    EXPIRED = "expired"
    UNKNOWN = "unknown"


class AuthError(Exception):
    """Raised when the user is not logged in or the session expired."""


AUTH_CHECK_SCRIPT = """
() => {
    // Primary check: look for common douyin login indicators
    // 1. Check cookie for session token
    if (document.cookie.indexOf('sessionid') !== -1) return "logged_in";

    // 2. Check for user avatar in the header area (top of page)
    var elements = document.querySelectorAll('img');
    for (var i = 0; i < elements.length; i++) {
        var src = (elements[i].getAttribute('src') || '');
        if (src.indexOf('douyin') !== -1 && (src.indexOf('avatar') !== -1 || src.indexOf('user') !== -1)) {
            return "logged_in";
        }
    }

    // 3. Check if login button visible
    var btns = document.querySelectorAll('button');
    for (var i = 0; i < btns.length; i++) {
        var t = (btns[i].textContent || '').trim();
        if (t === '登录' || t === 'Login') {
            var r = btns[i].getBoundingClientRect();
            if (r.width > 0 && r.height > 0) return "not_logged_in";
        }
    }

    // 4. Check for redirect to passport
    if (window.location.href.indexOf("passport.douyin.com") !== -1) return "expired";

    // 5. Fallback: if we can't find avatar but also no login button -> probably logged in
    return "logged_in";
}
"""


async def detect_auth_state(page: Page) -> AuthState:
    """Check multiple signals to determine login state."""
    result = await page.evaluate(AUTH_CHECK_SCRIPT)

    mapping = {
        "logged_in": AuthState.LOGGED_IN,
        "not_logged_in": AuthState.NOT_LOGGED_IN,
        "expired": AuthState.EXPIRED,
    }
    return mapping.get(result, AuthState.UNKNOWN)


async def assert_logged_in(page: Page) -> None:
    """Raise AuthError if the user is not logged in."""
    state = await detect_auth_state(page)
    if state == AuthState.LOGGED_IN:
        return

    msg = {
        AuthState.NOT_LOGGED_IN: "未登录状态，请先在浏览器中登录抖音",
        AuthState.EXPIRED: "登录已过期，请重新登录",
        AuthState.UNKNOWN: "无法确认登录状态，请检查页面",
    }.get(state, "未知认证状态")

    raise AuthError(msg)