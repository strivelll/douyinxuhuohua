"""Multi-level fallback selector system for Douyin DOM elements.

Each logical element is represented by a list of strategies tried in order.
This decouples selector logic from business logic and makes it easy to
add new fallback paths when Douyin's DOM changes.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from playwright.async_api import Page

# ── Strategy Types ────────────────────────────────────────


@dataclass
class SelectorStrategy:
    """One way to locate a DOM element.

    ``locate`` is an async callable that receives the Page and returns
    either a dict with at least ``{cx, cy}`` coordinates, or ``None``.
    """

    name: str
    locate: Callable[[Page], Awaitable[dict | None]]
    confidence: float = 0.5


async def _try_strategies(
    page: Page, strategies: list[SelectorStrategy], logger=None
) -> dict | None:
    """Run strategies in order; return first hit with highest confidence."""
    best: tuple[dict | None, float] = (None, 0.0)
    for s in strategies:
        try:
            result = await s.locate(page)
            if result and s.confidence > best[1]:
                best = (result, s.confidence)
                if s.confidence >= 0.9:
                    break
        except Exception as exc:
            if logger:
                logger(f"  selector '{s.name}' failed: {exc}")
            continue
    return best[0]


# ── Individual strategy builders ─────────────────────────


def _text_selector(tag: str, text: str, ancestor: str | None = None) -> SelectorStrategy:
    """Build a Playwright ``:has-text()`` strategy."""
    base = f'{tag}:has-text("{text}")'
    selector = f"{ancestor} {base}" if ancestor else base

    async def locate(page: Page) -> dict | None:
        el = page.locator(selector).first
        if await el.count() == 0:
            return None
        box = await el.bounding_box()
        if box and box["width"] > 0:
            return {"cx": box["x"] + box["width"] / 2, "cy": box["y"] + box["height"] / 2}
        return None

    return SelectorStrategy(name=f"text:{tag}('{text}')", locate=locate, confidence=0.7)


def _treewalker_text(text: str) -> SelectorStrategy:
    """TreeWalker scanning for text nodes containing *text* (v7 approach)."""

    async def locate(page: Page) -> dict | None:
        return await page.evaluate(
            f"""() => {{
                const w = document.createTreeWalker(document.body,4,null,false);
                let n;
                while (n = w.nextNode()) {{
                    const t = (n.textContent||'').trim();
                    if (t === '{text}') {{
                        let el = n.parentElement;
                        for (let j=0;j<10 && el && el!==document.body;j++) {{
                            if (el.getBoundingClientRect().width>10) break;
                            el = el.parentElement;
                        }}
                        const cr = el.getBoundingClientRect();
                        return {{cx: Math.round(cr.x+cr.width/2), cy: Math.round(cr.y+cr.height/2)}};
                    }}
                }}
                return null;
            }}""",
        )

    return SelectorStrategy(name=f"treewalker('{text}')", locate=locate, confidence=0.6)


def _css_selector(desc: str, css: str, confidence: float = 0.5) -> SelectorStrategy:
    """Generic CSS selector strategy."""

    async def locate(page: Page) -> dict | None:
        el = page.locator(css).first
        if await el.count() == 0:
            return None
        box = await el.bounding_box()
        if box and box["width"] > 0:
            return {"cx": box["x"] + box["width"] / 2, "cy": box["y"] + box["height"] / 2}
        return None

    return SelectorStrategy(name=f"css:{desc}", locate=locate, confidence=confidence)


def _panel_by_coordinates(x: int, y: int) -> SelectorStrategy:
    """Coordinate-based panel detection (v7 fallback)."""

    async def locate(page: Page) -> dict | None:
        return await page.evaluate(
            f"""() => {{
                for (const d of document.querySelectorAll('div')) {{
                    const r = d.getBoundingClientRect();
                    if (Math.abs(r.x-{x})<30 && Math.abs(r.y-{y})<20 && r.width>300) {{
                        return {{cx: r.x, cy: r.y, width: r.width, height: r.height}};
                    }}
                }}
                return null;
            }}""",
        )

    return SelectorStrategy(
        name=f"panel@({x},{y})", locate=locate, confidence=0.3
    )


# ── High-level selector chains ──────────────────────────

SIXIN_TRIGGER = [
    _treewalker_text("通知"),
    _treewalker_text("私信"),
    _treewalker_text("消息"),
]

PANEL_STRATEGIES = [
    _css_selector(
        "conversation-container",
        '[data-e2e="conversation-item"]',
        confidence=0.6,
    ),
    _panel_by_coordinates(1081, 56),
]

LOGIN_CHECK = [
    _css_selector("user-avatar", '[data-e2e="user-avatar"]', confidence=0.9),
    _css_selector("avatar-img", 'div[class*="avatar"] img', confidence=0.6),
]

POPUP_DISMISS = [
    "button:has-text('取消')",
    "button:has-text('我知道了')",
    "button:has-text('关闭')",
    "button:has-text('拒绝')",
    "button:has-text('忽略')",
    "button:has-text('不再提示')",
    'div[aria-label="关闭"]',
    'svg[class*="close"]',
]

# ── Contact scanning scripts (run inside page.evaluate) ──

SCAN_CONTACTS_JS = """
() => {
    // Find panel by multiple strategies
    let panel = null;

    // Strategy 1: data-e2e container
    const first = document.querySelector('[data-e2e="conversation-item"]');
    if (first) {
        let p = first.parentElement;
        for (let i = 0; i < 5 && p; i++) {
            const r = p.getBoundingClientRect();
            if (r.width > 300 && r.height > 100) { panel = p; break; }
            p = p.parentElement;
        }
    }

    // Strategy 2: coordinate fallback
    if (!panel) {
        for (const d of document.querySelectorAll('div')) {
            const r = d.getBoundingClientRect();
            if (Math.abs(r.x - 1081) < 30 && Math.abs(r.y - 56) < 20 && r.width > 300) {
                panel = d;
                break;
            }
        }
    }

    if (!panel) return [];

    const items = panel.querySelectorAll('[data-e2e="conversation-item"]');
    const res = [];

    for (const item of items) {
        // Name: try text content (most stable)
        const allText = (item.textContent || '').trim();
        const lines = allText.split('\\n').map(s => s.trim()).filter(Boolean);
        const name = lines[0] || '?';

        // Spark detection: img[src*=chat_days]
        const sparkImg = item.querySelector('img[src*="chat_days"]');
        const hasSpark = !!sparkImg;
        let sparkState = 'none';
        let days = '';

        if (sparkImg) {
            const src = sparkImg.getAttribute('src') || '';
            sparkState = src.includes('disable') ? 'disabled'
                : (src.includes('warning') || src.includes('expire')) ? 'expiring' : 'active';

            // Days text: look for a number sibling/adjacent to spark img
            const parent = sparkImg.parentElement;
            if (parent) {
                const spans = parent.querySelectorAll('span, div');
                for (const sp of spans) {
                    const t = (sp.textContent || '').trim();
                    if (/^\\d+$/.test(t)) { days = t; break; }
                }
            }
        }

        res.push({
            name: name.substring(0, 25),
            hasSpark,
            sparkState,
            days,
            target: hasSpark && sparkState === 'disabled',
        });
    }
    return res;
}
"""

FIND_CONTACT_JS = """
(name) => {
    for (const item of document.querySelectorAll('[data-e2e="conversation-item"]')) {
        const t = (item.textContent || '').trim();
        if (t.startsWith(name)) {
            item.click();
            return true;
        }
    }
    return false;
}
"""

FIND_INPUT_JS = """
() => {
    const selectors = [
        'div[contenteditable="true"]',
        'textarea',
        '[contenteditable]',
    ];
    for (const sel of selectors) {
        const el = document.querySelector(sel);
        if (!el) continue;
        const r = el.getBoundingClientRect();
        if (r.width > 50 && r.height > 20) return sel;
    }
    return null;
}
"""

CONFIRM_SENT_JS = """
(expected) => {
    const msgs = document.querySelectorAll(
        '[data-e2e="message-bubble"], [class*="message-item"], [class*="chat-message"]'
    );
    if (!msgs.length) return false;
    const last = msgs[msgs.length - 1];
    return (last.textContent || '').trim().includes(expected);
}
"""

WAIT_NAMES_JS = """
() => {
    let panel = null;
    for (const d of document.querySelectorAll('div')) {
        const r = d.getBoundingClientRect();
        if (Math.abs(r.x - 1081) < 30 && Math.abs(r.y - 56) < 20 && r.width > 300) {
            panel = d;
            break;
        }
    }
    if (!panel) return null;
    const names = Array.from(panel.querySelectorAll('[data-e2e="conversation-item"]'))
        .map(item => {
            const t = (item.textContent || '').trim();
            return t.split('\\n')[0].trim();
        })
        .filter(Boolean);
    return names.length >= 5 ? names : null;
}
"""

# ── Convenience accessors ────────────────────────────────


async def locate_sixin(page: Page) -> dict | None:
    """Locate the 私信 hover trigger. Returns {cx, cy} or None."""
    return await _try_strategies(page, SIXIN_TRIGGER)


async def locate_panel(page: Page) -> dict | None:
    """Locate the conversation panel. Returns {cx, cy, width, height} or None."""
    return await _try_strategies(page, PANEL_STRATEGIES)


# ── Popup dismiss helper ─────────────────────────────────


POPUP_EVALUATE_JS = """
() => {
    const texts = ["取消", "我知道了", "关闭", "拒绝", "忽略", "不再提示"];
    for (const t of texts) {
        for (const b of document.querySelectorAll('button,div,span')) {
            if ((b.textContent || '').trim() === t) {
                let el = b;
                for (let i = 0; i < 5 && el && el !== document.body; i++) {
                    if (el.tagName === 'BUTTON') break;
                    el = el.parentElement;
                }
                const cr = el.getBoundingClientRect();
                if (cr.width > 0 && cr.height > 0) {
                    return { cx: Math.round(cr.x + cr.width / 2), cy: Math.round(cr.y + cr.height / 2) };
                }
            }
        }
    }
    // Try generic close buttons
    for (const sel of ['div[aria-label="关闭"]', 'svg[class*="close"]']) {
        const el = document.querySelector(sel);
        if (el) {
            const cr = el.getBoundingClientRect();
            if (cr.width > 0) return { cx: Math.round(cr.x + cr.width / 2), cy: Math.round(cr.y + cr.height / 2) };
        }
    }
    return null;
}
"""