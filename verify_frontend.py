from playwright.sync_api import sync_playwright

def run(playwright):
    browser = playwright.chromium.launch()
    page = browser.new_page()

    # Chat page
    page.goto("http://127.0.0.1:5000/")
    page.screenshot(path="chat_page.png")

    # Settings page
    page.goto("http://127.0.0.1:5000/settings")
    page.screenshot(path="settings_page.png")

    browser.close()

with sync_playwright() as playwright:
    run(playwright)
