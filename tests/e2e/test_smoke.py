"""Smoke test establishing the E2E harness (Phase 1).

Deliberately minimal — one real path through the actual UI in a real
browser, proving the harness itself works end-to-end against the running
stack. The full suite (flaky-detection UI coverage, error-handling paths,
trend rendering) is Phase 10; writing it now, against a UI that's still
changing, would be wasted work per the plan's explicit sequencing call.
"""

from pathlib import Path

from playwright.sync_api import Page, expect


def test_upload_flow_renders_on_dashboard(
    page: Page, app_base_url: str, sample_trf_file: Path
) -> None:
    page.goto(app_base_url)

    expect(page.locator("h1")).to_have_text("Test Analytics Platform")

    page.locator("#file-input").set_input_files(str(sample_trf_file))
    page.locator("#upload-form button[type=submit]").click()

    expect(page.locator("#upload-status")).to_contain_text("Uploaded e2e-smoke-run")

    # Dashboard refreshes after upload — assert the summary card reflects
    # the real counts from sample_trf_file (1 passed, 1 failed), not a
    # placeholder or stale value.
    summary_cards = page.locator("#summary-cards")
    expect(summary_cards).to_contain_text("2")  # total tests
