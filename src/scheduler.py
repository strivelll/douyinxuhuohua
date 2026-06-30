"""Crontab installation and removal."""

import logging
import subprocess
import tempfile
from pathlib import Path

from config.settings import settings

logger = logging.getLogger(__name__)

CRON_MARKER = "# DOUYIN HUOHUA v8 - managed by douyin-huohua"


def _build_cron_line(script_path: str) -> str:
    """Build the crontab entry line."""
    project_dir = Path(script_path).resolve().parent.parent
    log_dir = project_dir / "log"
    log_dir.mkdir(parents=True, exist_ok=True)
    lock_file = "/tmp/huohua-v8.lock"
    expr = settings.cron_expression

    return (
        f"{CRON_MARKER}\n"
        f"{expr} cd {project_dir} "
        f"&& DISPLAY=:10 flock -xn {lock_file} "
        f"python3 -m src --cron "
        f">> {log_dir}/cron-$(date +\\%Y\\%m\\%d).log 2>&1"
    )


def _get_current_crontab() -> list[str]:
    """Get current crontab lines. Returns empty list if no crontab."""
    try:
        result = subprocess.run(
            ["crontab", "-l"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.splitlines()
        return []
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []


def _write_crontab(lines: list[str]) -> bool:
    """Write a new crontab from a list of lines."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".cron") as f:
        f.write("\n".join(lines) + "\n")
        tmp_path = f.name
    try:
        subprocess.run(
            ["crontab", tmp_path],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
        Path(tmp_path).unlink(missing_ok=True)
        return True
    except subprocess.CalledProcessError as exc:
        logger.error("crontab install failed: %s", exc.stderr)
        Path(tmp_path).unlink(missing_ok=True)
        return False


def install_crontab(script_path: str) -> bool:
    """Install the daily huohua crontab entry.

    Replaces any existing huohua entry. Uses flock to prevent concurrent runs.
    """
    current = _get_current_crontab()
    filtered = [line for line in current if CRON_MARKER not in line]

    new_line = _build_cron_line(script_path)
    filtered.append(new_line)

    return _write_crontab(filtered)


def remove_crontab() -> bool:
    """Remove the huohua crontab entry if present."""
    current = _get_current_crontab()
    filtered = [line for line in current if CRON_MARKER not in line]

    if len(filtered) == len(current):
        logger.info("No huohua crontab entry found")
        return True

    return _write_crontab(filtered)