from playwright.sync_api import sync_playwright


def create_browser(headless: bool = False):
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(headless=headless)
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        extra_http_headers={
            "Accept-Language": "pt-BR,pt;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        }
    )
    page = context.new_page()
    return playwright, browser, page


def close_browser(playwright, browser):
    browser.close()
    playwright.stop()