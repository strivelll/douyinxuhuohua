"""Feishu (飞书) webhook notification."""

import json
import logging
import urllib.request
from datetime import datetime

from config.settings import settings
from src.report import RunReport

logger = logging.getLogger(__name__)

FEISHU_CARD_TEMPLATE = {
    "msg_type": "interactive",
    "card": {
        "header": {
            "title": {"tag": "plain_text", "content": "🔥 抖音续火花执行报告"},
            "template": "green",
        },
        "elements": [],
    },
}


def _build_card(report: RunReport) -> dict:
    """Build a Feishu interactive card from a RunReport."""
    card = FEISHU_CARD_TEMPLATE.copy()
    elements = card["card"]["elements"]

    # Determine color based on results
    has_error = bool(report.error) or len(report.failed) > 0
    if has_error:
        card["card"]["header"]["template"] = "red"

    # Overview section
    elapsed = report.elapsed_str()
    elements.append(
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": (
                    f"**执行时间**: {report.start.strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"**耗时**: {elapsed}\n"
                    f"**登录状态**: {report.auth_state or 'N/A'}"
                ),
            },
        }
    )

    # Stats section
    stats_color = {
        "tag": "div",
        "text": {
            "tag": "lark_md",
            "content": (
                f"📊 **统计**\n"
                f"联系人: {report.contacts_found}　"
                f"🔥活跃: {report.active}　"
                f"💤熄灭: {report.disabled}　"
                f"💀无火花: {report.no_spark}\n"
                f"✅成功: {len(report.success)}　"
                f"❌失败: {len(report.failed)}　"
                f"🎯目标: {report.targets}"
            ),
        },
    }
    elements.append(stats_color)

    # Success list
    if report.success:
        success_text = "、".join(report.success)
        elements.append(
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"✅ **续火成功**: {success_text}",
                },
            }
        )

    # Failure list
    if report.failed:
        failed_lines = "\n".join(
            f"❌ {name}: {reason}" for name, reason in report.failed.items()
        )
        elements.append(
            {
                "tag": "div",
                "text": {"tag": "lark_md", "content": failed_lines},
            }
        )

    # Error info
    if report.error:
        elements.append(
            {
                "tag": "div",
                "text": {"tag": "lark_md", "content": f"⛔ **异常**: {report.error}"},
            }
        )

    # Screenshots
    if report.screenshot_paths:
        screens_text = "\n".join(report.screenshot_paths)
        elements.append(
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"📸 **截图**:\n{screens_text}",
                },
            }
        )

    # Timestamp footer
    elements.append(
        {
            "tag": "note",
            "elements": [
                {
                    "tag": "plain_text",
                    "content": f"🤖 自动推送 @ {datetime.now().strftime('%H:%M:%S')}",
                }
            ],
        }
    )

    return card


async def send_report(report: RunReport) -> bool:
    """Send the execution report to Feishu via webhook.

    Returns True if the webhook call succeeded, False otherwise.
    Failure is logged but does not raise (non-blocking).
    """
    webhook = settings.feishu_webhook
    if not webhook:
        logger.info("Feishu webhook not configured, skipping notification")
        return False

    payload = _build_card(report)
    data = json.dumps(payload).encode("utf-8")

    try:
        req = urllib.request.Request(
            webhook,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            if body.get("code") != 0:
                logger.warning("Feishu webhook returned error: %s", body)
                return False
            logger.info("Feishu notification sent successfully")
            return True
    except Exception as exc:
        logger.warning("Feishu webhook call failed: %s", exc)
        return False