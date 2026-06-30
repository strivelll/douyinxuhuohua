"""Report generation and output."""

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from src.auth import AuthState


@dataclass
class RunReport:
    success: list[str] = field(default_factory=list)
    failed: dict[str, str] = field(default_factory=dict)
    contacts_found: int = 0
    active: int = 0
    disabled: int = 0
    expiring: int = 0
    no_spark: int = 0
    targets: int = 0
    start: datetime = field(default_factory=datetime.now)
    elapsed: str = ""
    auth_state: str = ""
    error: str = ""
    screenshot_paths: list[str] = field(default_factory=list)

    def elapsed_str(self) -> str:
        if self.elapsed:
            return self.elapsed
        return str(datetime.now() - self.start).split(".")[0]

    def to_dict(self) -> dict:
        d = asdict(self)
        d["start"] = self.start.isoformat()
        d["elapsed"] = self.elapsed_str()
        return d


def print_report(r: RunReport) -> None:
    """Pretty-print the report to stdout."""
    elapsed = r.elapsed_str()
    print(f"\n{'='*55}")
    print(f"✅ 抖音续火花 — 执行报告")
    print(f"{'='*55}")
    print(f"  执行时间: {r.start.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  耗时: {elapsed}")
    print(f"\n{'─'*55}")
    print(f"  📊 联系人: {r.contacts_found}")
    print(f"  🔥 活跃:   {r.active}")
    print(f"  💤 熄灭:   {r.disabled}")
    print(f"  ⚠️ 将熄:   {r.expiring}")
    print(f"  💀 无火花: {r.no_spark}")
    print(f"  🎯 目标:   {r.targets}")
    print(f"  ✅ 成功:   {len(r.success)}")
    print(f"  ❌ 失败:   {len(r.failed)}")

    if r.success:
        print(f"\n  ✅ 已续火: {', '.join(r.success)}")
    if r.failed:
        print(f"\n  ❌ 失败详情:")
        for name, reason in r.failed.items():
            print(f"    {name}: {reason}")
    if r.error:
        print(f"\n  ⛔ 异常: {r.error}")
    if r.screenshot_paths:
        print(f"\n  📸 截图: {', '.join(r.screenshot_paths)}")
    print(f"{'='*55}\n")


def save_json_report(r: RunReport, path: Path) -> None:
    """Save a machine-readable JSON report."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(r.to_dict(), f, ensure_ascii=False, indent=2)