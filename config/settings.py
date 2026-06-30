from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class HuohuaSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="HUOHUA_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Browser
    viewport_width: int = 1440
    viewport_height: int = 900
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    )
    browser_args: list[str] = [
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-blink-features=AutomationControlled",
    ]
    profile_dir: Path = Field(default=Path("./profile"))
    locale: str = "zh-CN"
    timezone: str = "Asia/Shanghai"

    # Navigation
    home_url: str = "https://www.douyin.com/"
    home_timeout_ms: int = 30000
    hover_retry_seconds: int = 20
    panel_wait_seconds: int = 15
    panel_coordinates_x: int = 1081  # fallback only
    panel_coordinates_y: int = 56   # fallback only

    # Message
    message_default: str = "\U0001f525"
    send_delay_min: float = 2.0
    send_delay_max: float = 3.5

    # Robustness
    max_retries: int = 3
    retry_base_delay_s: float = 2.0
    retry_max_delay_s: float = 30.0

    # Scheduling
    cron_expression: str = "0 23 * * *"
    cron_log_dir: Path = Field(default=Path("./log"))

    # Screenshots
    screenshot_dir: Path = Field(default=Path("./screenshots"))

    # Detection thresholds
    min_contact_count: int = 5

    # Notifier
    feishu_webhook: str = ""


settings = HuohuaSettings()