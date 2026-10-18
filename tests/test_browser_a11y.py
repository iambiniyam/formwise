"""Browser-level accessibility checks for the interactive form flow."""

from __future__ import annotations

import os
import socket
import threading
import time
from pathlib import Path

import pytest
import uvicorn
from reportlab.pdfgen import canvas

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright

from formwise.server import app

AXE = Path(__file__).with_name("axe.min.js")


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture(scope="module")
def live_server(tmp_path_factory):
    home = tmp_path_factory.mktemp("formwise-home")
    old = os.environ.get("FORMWISE_HOME")
    os.environ["FORMWISE_HOME"] = str(home)
    port = free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                break
        except OSError:
            time.sleep(0.1)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    thread.join(timeout=5)
    if old is None:
        os.environ.pop("FORMWISE_HOME", None)
    else:
        os.environ["FORMWISE_HOME"] = old


def axe_violations(page) -> list[dict]:
    page.add_script_tag(path=str(AXE))
    report = page.evaluate(
        """async () => await axe.run(document, {
          runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21aa"] }
        })"""
    )
    return [item for item in report["violations"] if item["impact"] in {"serious", "critical"}]


def test_initial_and_scanned_form_states(live_server, tmp_path):
    source = tmp_path / "scan.pdf"
    page = canvas.Canvas(str(source), pagesize=(612, 792))
    page.setFont("Helvetica-Bold", 20)
    page.drawString(60, 720, "VOLUNTEER FORM")
    page.setFont("Helvetica", 12)
    page.drawString(60, 680, "Name:")
    page.drawString(60, 640, "Email:")
    page.showPage()
    page.save()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(viewport={"width": 1182, "height": 900})
        tab = context.new_page()
        tab.goto(live_server, wait_until="networkidle")
        assert axe_violations(tab) == []

        tab.set_input_files("#file", str(source))
        tab.click("#inspect")
        tab.wait_for_selector("#result:not([hidden])", timeout=30000)
        assert axe_violations(tab) == []

        box = tab.locator("#preview").bounding_box()
        tab.mouse.click(box["x"] + box["width"] * 0.3, box["y"] + box["height"] * 0.25)
        tab.wait_for_selector('[data-overlay="0"]', timeout=10000)
        tab.fill('[data-overlay="0"]', "Jane Doe")
        tab.click("#fill")
        tab.wait_for_selector("#download:not([hidden])", timeout=30000)
        assert axe_violations(tab) == []
        browser.close()
