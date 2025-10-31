# from playwright.sync_api import sync_playwright

# with sync_playwright() as p:
#     browser = p.firefox.launch(headless=False)
#     page = browser.new_page()
#     page.goto("https://www.google.com")
    
#     # 작업 수행
#     page.get_by_role("link", name="Gmail").click()
#     page.get_by_role("link", name="Sign In").click()


#     # 사용자 입력 대기 (Enter 키 누를 때까지 브라우저 창 유지)
#     input("Press Enter to close the browser...")
    
#     browser.close()



# import pytest
# import re
# from playwright.sync_api import Page, sync_playwright, expect


# # Fixture: 각 테스트 전후로 실행되는 설정
# @pytest.fixture(scope="function", autouse=True)
# def setup_and_teardown(page: Page):
#     """
#     각 테스트 실행 전에 setup, 후에 teardown을 수행합니다.
#     - Setup: 특정 웹사이트로 이동
#     - Teardown: 테스트 후 정리 작업 (필요시)
#     """
#     print("\n🔧 테스트 시작 - 초기 설정 중...")
#     page.goto("https://playwright.dev/")
#     yield  # 여기서 테스트가 실행됨
#     print("\n🧹 테스트 종료 - 정리 중...")


# def test_page_title(page: Page):
#     """
#     테스트 1: 페이지 제목 검증
#     - 페이지가 제목에 "Playwright"를 포함하는지 확인
#     """
#     print("\n✅ 테스트 1: 페이지 제목 검증")
#     expect(page).to_have_title(re.compile("Playwright"))
#     print("✓ 페이지 제목이 'Playwright'를 포함함")


# def test_navigation_and_link_click(page: Page):
#     """
#     테스트 2: 네비게이션과 링크 클릭
#     - "Get started" 링크를 찾아 클릭
#     - 클릭 후 특정 제목이 보이는지 확인
#     """
#     print("\n✅ 테스트 2: 링크 클릭 및 네비게이션")
    
#     # 행동(Action): "Get started" 링크 찾기 및 클릭
#     print("  - 'Get started' 링크 클릭 중...")
#     page.get_by_role("link", name="Get started").click()
    
#     # 검증(Assertion): "Installation" 제목이 보이는지 확인
#     print("  - 페이지 로드 확인...")
#     expect(page.get_by_role("heading", name="Installation")).to_be_visible()
#     print("✓ 'Installation' 제목이 화면에 표시됨")


# def test_url_verification(page: Page):
#     """
#     테스트 3: URL 검증
#     - 현재 페이지의 URL이 올바른지 확인
#     """
#     print("\n✅ 테스트 3: URL 검증")
    
#     # 현재 URL이 playwright.dev인지 확인
#     expect(page).to_have_url("https://playwright.dev/")
#     print("✓ 현재 URL이 정확함")


# def test_search_and_interaction(page: Page):
#     """
#     테스트 4: 검색 기능 테스트 (복합 행동)
#     - 검색창 찾기
#     - 텍스트 입력(fill)
#     - 특정 요소가 활성화되었는지 확인
#     """
#     print("\n✅ 테스트 4: 검색 기능 및 상호작용")
    
#     # 행동 1: 페이지 스크롤해서 검색 관련 요소 찾기
#     print("  - 검색 요소 찾는 중...")
    
#     # 페이지의 주요 텍스트 찾기
#     heading = page.get_by_role("heading", name=re.compile("Get started", re.IGNORECASE))
    
#     # 검증: 제목이 보이고 활성화되었는지 확인
#     expect(heading).to_be_visible()
#     expect(heading).to_be_enabled()
#     print("✓ 제목이 보이고 활성화됨")


# def test_multiple_elements_count(page: Page):
#     """
#     테스트 5: 여러 요소 개수 확인
#     - 페이지의 모든 링크 개수 확인
#     """
#     print("\n✅ 테스트 5: 페이지 요소 개수 확인")
    
#     # 페이지의 모든 링크 찾기
#     links = page.get_by_role("link")
    
#     # 링크가 최소 1개 이상 있는지 확인
#     expect(links).to_have_count(lambda x: x > 0)
#     print(f"✓ 페이지에 링크가 여러 개 존재함")


# def test_attribute_verification(page: Page):
#     """
#     테스트 6: 요소의 속성 검증
#     - 특정 요소가 특정 속성을 가지고 있는지 확인
#     """
#     print("\n✅ 테스트 6: 요소 속성 검증")
    
#     # "Get started" 링크의 href 속성 확인
#     link = page.get_by_role("link", name="Get started")
#     expect(link).to_have_attribute("href", re.compile("/docs/intro"))
#     print("✓ 링크의 href 속성이 올바름")


# def test_text_content_verification(page: Page):
#     """
#     테스트 7: 요소의 텍스트 검증
#     - 요소가 특정 텍스트를 포함하는지 확인
#     """
#     print("\n✅ 테스트 7: 텍스트 콘텐츠 검증")
    
#     # 페이지 메인 제목 확인
#     main_heading = page.get_by_role("heading").first
#     expect(main_heading).to_contain_text("Playwright")
#     print("✓ 페이지에 'Playwright' 텍스트가 포함됨")


# # if __name__ == "__main__":
# #     # pytest로 이 파일의 모든 테스트를 실행
# #     # 터미널에서 실행: pytest test_comprehensive.py -v --headed
# #     input("Press Enter to close the browser...")
# #     print("Playwright 테스트 종합 예시 시작...")





# if __name__ == "__main__":
#     print("🚀 Playwright 테스트 직접 실행 시작...\n")
    
#     with sync_playwright() as p:
#         browser = p.firefox.launch(headless=False)
#         context = browser.new_context()
#         page = context.new_page()
        
#         # 초기 설정
#         print("🔧 테스트 시작 - 초기 설정 중...")
#         page.goto("https://playwright.dev/")
        
#         try:
#             # 각 테스트 함수 호출
#             test_page_title(page)
            
#             test_url_verification(page)
            
#             test_text_content_verification(page)
            
#             test_multiple_elements_count(page)
            
#             test_attribute_verification(page)
            
#             test_search_and_interaction(page)
            
#             test_navigation_and_link_click(page)
            
#             print("\n" + "="*50)
#             print("✅ 모든 테스트 완료!")
#             print("="*50)
            
#         except Exception as e:
#             print(f"\n❌ 테스트 실패: {e}")
        
#         finally:
#             # 정리 작업
#             print("\n🧹 테스트 종료 - 정리 중...")
            
#             # 사용자 입력 대기 (Enter 키 누를 때까지 브라우저 창 유지)
#             input("\n👉 Press Enter to close the browser...")
            
#             context.close()
#             browser.close()
#             print("✓ 브라우저 종료됨")


#########################################################33

# from playwright.sync_api import sync_playwright

# # Playwright 실행
# with sync_playwright() as p:
#     # Chromium 브라우저 시작
#     browser = p.firefox.launch(headless=False)
#     page = browser.new_page()
    
#     # 페이지 이동
#     page.goto("https://www.google.com")
#     print("Page Title:", page.title())  # 페이지 제목 출력
#     input("\n👉 Press Enter to close the browser...")

#     # 사용자 입력 대기 (Enter 키 누를 때까지 브라우저 창 유지)
             
#     # 브라우저 종료
#     browser.close()

#########################################################

from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    # 브라우저(Chromium) 열기
    browser = p.firefox.launch(headless=False)  # headless=False로 두면 창이 뜸
    page = browser.new_page()
    # 웹사이트 접속
    page.goto('https://www.cau.ac.kr')
    # 타이틀 출력
    print(page.title())
    # 특정 요소의 텍스트 추출
    print(page.text_content('h1'))
    # 스크린샷 저장
    page.screenshot(path='example.png')

    input("\n👉 Press Enter to close the browser...")

    browser.close()
