#!/usr/bin/env python3
"""Douyin Huohua v8 — CLI entry point.

Usage:
    python -m src                        # Default run (send 🔥 to expired sparks)
    python -m src --message "早安"        # Custom message
    python -m src --dry-run              # Scan only, no sends
    python -m src --cron                 # Cron mode (JSON report, Feishu notify)
    python -m src --install-cron         # Install daily crontab
    python -m src --remove-cron          # Remove crontab
"""

import argparse
import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path

from config.settings import settings
from src.auth import AuthError, assert_logged_in
from src.browser import cleanup_locks, create_context
from src.contacts import scan_contacts
from src.messenger import send_message_to_contact
from src.navigation import back_to_panel, dismiss_all_popups, load_home, open_panel, wait_names_load
from src.notifier import send_report
from src.report import RunReport, print_report, save_json_report
from src.scheduler import install_crontab, remove_crontab

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="抖音批量续火花 v8")
    p.add_argument("--message", "-m", default=settings.message_default, help="发送的消息内容")
    p.add_argument("--dry-run", "-n", action="store_true", help="仅扫描，不发送消息")
    p.add_argument("--cron", action="store_true", help="定时任务模式（JSON 报告 + 飞书推送）")
    p.add_argument("--install-cron", action="store_true", help="安装每日定时任务")
    p.add_argument("--remove-cron", action="store_true", help="移除定时任务")
    p.add_argument("--notify", action="store_true", help="手动触发飞书推送")
    return p.parse_args()


def _setup_logging(cron_mode: bool) -> None:
    level = logging.INFO if cron_mode else logging.DEBUG
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )


async def run(args: argparse.Namespace) -> RunReport:
    """Main execution flow. Returns a RunReport."""
    report = RunReport(start=datetime.now())
    screenshot_paths: list[Path] = []

    try:
        cleanup_locks()
        from playwright.async_api import async_playwright

        async with async_playwright() as pw:
            ctx = await create_context(pw)
            page = await ctx.new_page()

            # 1. Load home
            await load_home(page)

            # 2. Dismiss popups
            dismissed = await dismiss_all_popups(page)
            logger.info("弹窗已关闭: %d", dismissed)

            # 3. Screenshot: home
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            home_shot = settings.screenshot_dir / f"h1-home_{ts}.png"
            await page.screenshot(path=str(home_shot))
            screenshot_paths.append(home_shot)

            # 4. Check login state
            try:
                await assert_logged_in(page)
                report.auth_state = "logged_in"
            except AuthError as e:
                report.auth_state = "not_logged_in"
                report.error = str(e)
                await ctx.close()
                return report

            # 5. Open private message panel
            if not await open_panel(page):
                report.error = "无法打开私信面板"
                await ctx.close()
                return report

            # 6. Screenshot: panel
            panel_shot = settings.screenshot_dir / f"h2-panel_{ts}.png"
            await page.screenshot(path=str(panel_shot))
            screenshot_paths.append(panel_shot)

            # 7. Wait for names to load
            names = await wait_names_load(page)
            logger.info("联系人加载: %d 人", len(names))

            # 8. Scan contacts
            scan = await scan_contacts(page)
            report.contacts_found = len(scan.contacts)
            report.active = len(scan.active)
            report.disabled = len(scan.disabled)
            report.expiring = len(scan.expiring)
            report.no_spark = len(scan.no_spark)
            report.targets = len(scan.targets)

            # 9. Send messages (unless dry-run)
            if scan.targets and not args.dry_run:
                message = args.message or settings.message_default
                for idx, contact in enumerate(scan.targets):
                    ok, err = await send_message_to_contact(page, contact, message)
                    if ok:
                        report.success.append(contact.name)
                    else:
                        report.failed[contact.name] = err or "未知错误"
                    if idx < len(scan.targets) - 1:
                        await back_to_panel(page)

            # 10. Screenshot: done
            done_shot = settings.screenshot_dir / f"h3-done_{ts}.png"
            await page.screenshot(path=str(done_shot))
            screenshot_paths.append(done_shot)

            await ctx.close()

    except Exception as exc:
        report.error = f"{type(exc).__name__}: {exc}"
        logger.exception("运行异常")

    report.elapsed = str(datetime.now() - report.start).split(".")[0]
    report.screenshot_paths = [str(p) for p in screenshot_paths]
    return report


async def main_async() -> None:
    args = parse_args()
    _setup_logging(args.cron)

    # Handle scheduling commands
    if args.install_cron:
        script = Path(sys.argv[0]).resolve()
        ok = install_crontab(str(script))
        print("✅ 定时任务已安装" if ok else "❌ 安装失败")
        return
    if args.remove_cron:
        ok = remove_crontab()
        print("✅ 定时任务已移除" if ok else "❌ 移除失败")
        return

    # Main run
    report = await run(args)
    print_report(report)

    # Save JSON report in cron mode
    if args.cron:
        report_path = Path(settings.cron_log_dir) / "report-latest.json"
        save_json_report(report, report_path)
        day_log = Path(settings.cron_log_dir) / f"cron-{datetime.now().strftime('%Y%m%d')}.log"
        save_json_report(report, day_log)

    # Feishu notification (cron mode auto-sends, manual mode with --notify)
    if args.cron or args.notify:
        await send_report(report)


def main() -> None:
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print("\n⛔ 用户中断")
        sys.exit(1)


if __name__ == "__main__":
    main()