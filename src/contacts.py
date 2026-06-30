"""Contact scanning and spark status detection."""

from dataclasses import dataclass

from playwright.async_api import Page

from src.selectors import SCAN_CONTACTS_JS


@dataclass
class ContactInfo:
    name: str
    has_spark: bool
    spark_state: str  # "active" | "disabled" | "expiring" | "none"
    days: str
    target: bool  # has_spark AND spark_state == "disabled"


@dataclass
class ScanReport:
    contacts: list[ContactInfo]
    active: list[ContactInfo]
    disabled: list[ContactInfo]
    expiring: list[ContactInfo]
    no_spark: list[ContactInfo]
    targets: list[ContactInfo]


def _build_scan(contacts: list[dict]) -> ScanReport:
    parsed = []
    for c in contacts:
        ci = ContactInfo(
            name=c.get("name", "?"),
            has_spark=c.get("hasSpark", False),
            spark_state=c.get("sparkState", "none"),
            days=c.get("days", ""),
            target=c.get("target", False),
        )
        parsed.append(ci)

    return ScanReport(
        contacts=parsed,
        active=[c for c in parsed if c.spark_state == "active"],
        disabled=[c for c in parsed if c.spark_state == "disabled"],
        expiring=[c for c in parsed if c.spark_state == "expiring"],
        no_spark=[c for c in parsed if c.spark_state == "none"],
        targets=[c for c in parsed if c.target],
    )


async def scan_contacts(page: Page) -> ScanReport:
    """Scan the conversation panel and detect spark states for all contacts."""
    raw = await page.evaluate(SCAN_CONTACTS_JS)
    return _build_scan(raw or [])