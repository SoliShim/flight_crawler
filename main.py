from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.firefox.launch(headless=False)
    page = browser.new_page()
    page.goto("https://www.google.com")
    
    # 작업 수행
    page.get_by_role("link", name="Gmail").click()
    page.get_by_role("link", name="Sign In").click()


    # 사용자 입력 대기 (Enter 키 누를 때까지 브라우저 창 유지)
    input("Press Enter to close the browser...")
    
    browser.close()
