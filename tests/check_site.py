"""Browser checks. Optional tooling: Python + Playwright + Chromium.

Run from the repository root: python tests/check_site.py
The website itself has no Python or Playwright dependency.
"""

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.request import urlopen
import re
import xml.etree.ElementTree as ET

from playwright.sync_api import sync_playwright, expect


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / ".test-artifacts"
UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
checks = 0


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


def check(condition, name):
    global checks
    assert condition, name
    checks += 1


def values(page):
    return page.locator(".uuid-value").all_text_contents()


def generate(page, count):
    page.locator("#quantity").fill(str(count))
    page.locator("#generate-button").click()


CLIPBOARD = """
window.__copied = null;
window.__rejectCopy = false;
window.__deferCopy = false;
Object.defineProperty(navigator, 'clipboard', { configurable: true, value: {
  writeText: async (text) => {
    if (window.__deferCopy) await new Promise(resolve => window.__resolveCopy = resolve);
    if (window.__rejectCopy) throw new Error('Permission denied');
    window.__copied = text;
  }
}});
"""


def run():
    ARTIFACTS.mkdir(exist_ok=True)
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(ROOT / "public")))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://localhost:{server.server_port}"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            for path, language in [("/", "en"), ("/zh/", "zh-CN")]:
                context = browser.new_context(viewport={"width": 1440, "height": 1120})
                context.add_init_script(CLIPBOARD)
                page = context.new_page()
                requests, errors = [], []
                page.on("request", lambda request: requests.append(request.url))
                page.on("pageerror", lambda error: errors.append(str(error)))
                response = page.goto(base + path, wait_until="networkidle")
                check(response.status == 200, "page is served")
                check(page.locator("html").get_attribute("lang") == language, "page language")
                check(page.locator("h1").count() == 1, "one main heading")
                check(page.locator("link[rel=canonical]").get_attribute("href") == "https://example.com" + path, "self canonical")
                check(page.locator("link[hreflang]").count() == 3, "language links")
                check(page.locator("#quantity").input_value() == "1", "default count")
                check(page.locator("#copy-all").is_disabled() and not values(page), "initial empty state")
                label = "zh" if language == "zh-CN" else "en"
                page.screenshot(path=str(ARTIFACTS / f"{label}-desktop.png"), full_page=True)
                request_count = len(requests)

                for count in (1, 10, 100):
                    generate(page, count)
                    found = values(page)
                    check(len(found) == count, f"{language}: count {count}")
                    check(len(set(found)) == count and all(UUID.fullmatch(value) for value in found), "valid unique v4 batch")

                before = values(page)
                generate(page, 10)
                check(len(values(page)) == 10 and values(page) != before, "new batch replaces old list")
                before = values(page)
                for invalid in ("", "0", "-1", "1.5", "101", "abc", "1e2", "Infinity"):
                    generate(page, invalid)
                    check(values(page) == before, "invalid count preserves results")
                    check(page.locator("#quantity").get_attribute("aria-invalid") == "true", "invalid field exposed accessibly")
                    check(page.locator("#quantity-error").inner_text() == ("请输入 1 到 100 之间的整数。" if label == "zh" else "Enter a whole number between 1 and 100."), "localized validation")
                generate(page, 10)

                page.locator(".copy-button").first.click()
                expect(page.locator("#status")).to_have_attribute("data-state", "success")
                check(page.evaluate("window.__copied") == values(page)[0], "copy one exact UUID")
                page.locator("#copy-all").click()
                expect(page.locator("#status")).to_contain_text("已复制全部" if label == "zh" else "All UUIDs")
                check(page.evaluate("window.__copied") == "\n".join(values(page)), "copy all exact newline list")

                page.evaluate("window.__rejectCopy = true")
                page.locator("#copy-all").click()
                expect(page.locator("#manual-copy")).to_be_visible()
                check(page.locator("#status").get_attribute("data-state") == "error", "clipboard rejection reported")
                check(page.locator("#manual-text").input_value() == "\n".join(values(page)), "manual copy contains requested results")
                check(page.evaluate("document.activeElement.id") == "manual-text", "manual copy receives focus")
                page.evaluate("window.__rejectCopy = false")
                page.locator(".copy-button").last.click()
                expect(page.locator("#manual-copy")).to_be_hidden()

                page.evaluate("window.__deferCopy = true")
                page.locator("#copy-all").click()
                expect(page.locator("#copy-all")).to_be_disabled()
                generate(page, 1)
                page.evaluate("window.__resolveCopy(); window.__deferCopy = false")
                expect(page.locator("#status")).to_contain_text("已生成 1" if label == "zh" else "1 UUID generated")
                check(not page.locator("#copy-all").is_disabled(), "pending copy cannot disable new batch")

                page.evaluate("""() => {
                  window.__nativeUUID = crypto.randomUUID.bind(crypto);
                  const a = '00000000-0000-4000-8000-000000000001';
                  const b = '00000000-0000-4000-8000-000000000002';
                  const sequence = [a, a, b];
                  Object.defineProperty(crypto, 'randomUUID', {configurable: true, value: () => sequence.shift()});
                }""")
                generate(page, 2)
                check(len(set(values(page))) == 2, "duplicate is retried")
                before = values(page)
                page.evaluate("Object.defineProperty(crypto, 'randomUUID', {configurable:true, value: () => '00000000-0000-4000-8000-000000000001'})")
                generate(page, 2)
                check(values(page) == before and page.locator("#status").get_attribute("data-state") == "error", "bounded retry preserves previous batch on failure")
                page.evaluate("Object.defineProperty(crypto, 'randomUUID', {configurable:true, value: () => {throw new Error('generator failed')}})")
                generate(page, 1)
                check(values(page) == before, "generator exception preserves results")
                page.evaluate("Object.defineProperty(crypto, 'randomUUID', {configurable:true, value: undefined})")
                generate(page, 1)
                check(values(page) == before and ("不支持" if label == "zh" else "cannot generate") in page.locator("#status").inner_text(), "unsupported browser message")
                page.evaluate("Object.defineProperty(crypto, 'randomUUID', {configurable:true, value: window.__nativeUUID})")

                page.locator("#quantity").fill("1")
                page.locator("#quantity").press("Enter")
                check(len(values(page)) == 1, "keyboard form submission")
                page.keyboard.press("Tab")
                check(page.evaluate("document.activeElement.id") == "generate-button", "keyboard reaches generate button")
                check(page.locator("#generate-button").evaluate("el => getComputedStyle(el).outlineStyle") != "none", "visible keyboard focus")
                page.keyboard.press("Tab")
                check(page.evaluate("document.activeElement.className") == "copy-button", "keyboard reaches row copy")

                for width in (320, 360, 390):
                    page.set_viewport_size({"width": width, "height": 844})
                    generate(page, 100)
                    check(page.evaluate("document.documentElement.scrollWidth <= innerWidth"), f"no horizontal overflow at {width}px")
                    bounds = page.locator("#generate-button").bounding_box()
                    check(bounds["width"] >= 44 and bounds["height"] >= 44 and bounds["x"] + bounds["width"] <= width, "mobile generate button fits")
                page.set_viewport_size({"width": 360, "height": 844})
                generate(page, 1)
                page.evaluate("window.scrollTo(0, 0)")
                page.screenshot(path=str(ARTIFACTS / f"{label}-mobile.png"), full_page=True)
                check(len(requests) == request_count, "generation and copying make no network requests")
                check(not errors, "no browser exceptions")
                target = "/" if label == "zh" else "/zh/"
                page.locator(f".language-nav a[href='{target}']").click()
                expect(page.locator("html")).to_have_attribute("lang", "en" if label == "zh" else "zh-CN")
                check(not values(page) and page.locator("#quantity").input_value() == "1", "language switch resets results")
                context.close()

            mobile = browser.new_context(viewport={"width": 360, "height": 800}, is_mobile=True, has_touch=True)
            mobile.add_init_script(CLIPBOARD)
            page = mobile.new_page()
            page.goto(base + "/zh/")
            page.locator("#generate-button").tap()
            page.locator(".copy-button").tap()
            expect(page.locator("#status")).to_have_text("已复制")
            check(page.evaluate("window.__copied") == values(page)[0], "touch generation and copy")
            mobile.close()

            no_js = browser.new_context(java_script_enabled=False)
            page = no_js.new_page()
            page.goto(base + "/")
            check(page.locator("h1").inner_text() == "UUID Generator.", "static heading readable without JavaScript")
            check(page.locator(".noscript-notice").is_visible(), "no JavaScript message")
            no_js.close()
            browser.close()

        with urlopen(base + "/sitemap.xml") as response:
            sitemap = ET.fromstring(response.read())
            check(response.status == 200, "sitemap publicly served")
        addresses = [element.text for element in sitemap.findall("{*}url/{*}loc")]
        check(addresses == ["https://example.com/", "https://example.com/zh/"], "two placeholder sitemap addresses")
        with urlopen(base + "/robots.txt") as response:
            check(b"Allow: /" in response.read(), "robots allows crawling")
        print(f"PASS: {checks} checks. Screenshots: {ARTIFACTS}")
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    run()
