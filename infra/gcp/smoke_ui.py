"""Production UI smoke for the judge-facing portal. Synthetic data only. No Voximplant."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DEFAULT_UI = "https://eir-ui-658898892127.us-central1.run.app"
SCREEN_DIR = Path("artifacts/ui-qa")


def main() -> int:
    parser = argparse.ArgumentParser(description="EIR production browser QA")
    parser.add_argument("--ui-url", default=DEFAULT_UI)
    parser.add_argument("--headed", action="store_true")
    args = parser.parse_args()
    ui = args.ui_url.rstrip("/")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("SKIP playwright is not installed")
        return 0

    SCREEN_DIR.mkdir(parents=True, exist_ok=True)
    failures: list[str] = []
    console_errors: list[str] = []
    network_errors: list[str] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=not args.headed)
        for name, width, height in (("desktop", 1440, 900), ("mobile", 390, 844)):
            page = browser.new_page(viewport={"width": width, "height": height})
            page.on(
                "console",
                lambda message, bucket=console_errors, label=name: (
                    bucket.append(f"{label} {message.type} {message.text}")
                    if message.type in {"error"}
                    else None
                ),
            )
            page.on(
                "pageerror",
                lambda error, bucket=console_errors, label=name: bucket.append(
                    f"{label} uncaught {error}"
                ),
            )
            page.on(
                "response",
                lambda response, bucket=network_errors, label=name: (
                    bucket.append(f"{label} {response.status} {response.url}")
                    if response.status >= 400 and "/api/" in response.url
                    else None
                ),
            )

            def open_nav() -> None:
                if width < 1024:
                    trigger = page.get_by_role("button", name="Open menu")
                    if trigger.is_visible():
                        trigger.click()

            def shot(label: str) -> None:
                page.screenshot(path=str(SCREEN_DIR / f"{label}-{name}.png"), full_page=True)

            page.goto(ui, wait_until="networkidle")
            if "Healthcare Agent Fleet" not in page.content():
                failures.append(f"{name} landing missing headline")
            shot("landing")

            page.get_by_role("link", name="Sign in by role").first.click()
            page.wait_for_url("**/login")
            page.get_by_role("heading", name="Alex Rivera").wait_for()
            shot("login")

            page.get_by_role("button", name="Continue as Alex Rivera").click()
            page.wait_for_url("**/patient")
            page.get_by_text("Next appointment").wait_for()
            shot("patient-home")

            open_nav()
            page.get_by_role("link", name="Appointments").first.click()
            page.wait_for_url("**/patient/appointments")
            shot("patient-appointments")

            open_nav()
            page.get_by_role("link", name="Ask EIR").first.click()
            page.wait_for_url("**/patient/assistant")
            shot("patient-assistant")
            page.get_by_role("button", name="Show my appointments").click()
            page.wait_for_timeout(6000)

            open_nav()
            page.get_by_role("link", name="Switch demo role").first.click()
            page.wait_for_url("**/login")
            page.get_by_role("button", name="Continue as Dr. Maya Chen").click()
            page.wait_for_url("**/clinician")
            page.get_by_text("Reviews waiting").wait_for()
            shot("clinician-home")
            open_nav()
            page.get_by_role("link", name="Schedule").first.click()
            page.wait_for_url("**/clinician/schedule")
            shot("clinician-schedule")
            open_nav()
            page.get_by_role("link", name="Reviews").first.click()
            page.wait_for_url("**/clinician/reviews")
            shot("clinician-reviews")

            open_nav()
            page.get_by_role("link", name="Switch demo role").first.click()
            page.wait_for_url("**/login")
            page.get_by_role("button", name="Continue as Operations Admin").click()
            page.wait_for_url("**/admin")
            page.get_by_text("Appointments today").wait_for()
            shot("admin-home")
            open_nav()
            page.get_by_role("link", name="Fleet").first.click()
            page.wait_for_url("**/admin/fleet")
            page.get_by_text("Managed platform").wait_for()
            shot("admin-fleet")

            overflow = page.evaluate(
                "() => document.documentElement.scrollWidth > "
                "document.documentElement.clientWidth + 1"
            )
            if overflow:
                failures.append(f"{name} horizontal overflow")
            page.close()

        browser.close()

    unexpected_console = [
        item
        for item in console_errors
        if "favicon" not in item.lower() and "hydration" not in item.lower()
    ]
    unexpected_network = [item for item in network_errors if "401" not in item]
    if unexpected_console:
        failures.extend(unexpected_console)
    if unexpected_network:
        failures.extend(unexpected_network)
    payload = {
        "status": "ok" if not failures else "fail",
        "ui": ui,
        "console_errors": unexpected_console,
        "network_errors": unexpected_network,
        "screenshots": str(SCREEN_DIR),
    }
    print(json.dumps(payload, indent=2))
    if failures:
        for item in failures:
            print(f"FAIL {item}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
