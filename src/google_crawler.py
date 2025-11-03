import asyncio
from playwright.async_api import async_playwright
from utils import generate_random_profile, print_profile_info, generate_random_decimal

async def scrape_google_flight():
    """
    구글 플라이트를 크롤링하는 함수
    """
    print("구글 플라이트 크롤링을 시작합니다...")
    async with async_playwright() as p: 
        #playwright 라이브러리 초기화하고 p라고 하겠다.
        #with는 블록이 끝나면 자동으로 리소스 정리하라는 의미
        profile = generate_random_profile()
        print_profile_info(profile)
        
        browser = await p.firefox.launch(headless=False)
        #await의 의미는 실행 하고 I\O작업이 끝날때까지 대기하라는 의미
        #await이 없으면 안 된다!

        # 랜덤 프로필을 context에 적용
        context = await browser.new_context(
            user_agent=profile['user_agent'],
            locale=profile['locale'],
            timezone_id=profile['timezone_id'],
            viewport=profile['viewport'],
        )

        page = await context.new_page() 
        # browser를 실행합니다. headless=False로 설정하면 브라우저가 실제로 열리는 것을 볼 수 있습니다.


        # 스카이스캐너 웹사이트로 이동합니다.
        await page.goto("https://www.google.com/travel/flights?hl=ko-KR")
        print("구글 플라이트 페이지에 접속했습니다.")
        await asyncio.sleep(generate_random_decimal())



        #요소 찾기 (로케이터)
        await page.get_by_label('출발지가 어디인가요?').fill("") #exact=True는 정확히 일치하는 요소를 찾겠다는 의미
        await page.get_by_label('출발지가 어디인가요?').type("ICN")
        await asyncio.sleep(generate_random_decimal())
        # await page.get_by_role('textbox', name='사용자 ID를 입력해주세요.', exact=True).type('solomon1221')
        # await asyncio.sleep(generate_random_decimal())
        # await page.get_by_role('textbox', name='비밀번호를 입력해주세요.', exact=True).type('solomon3F88!')
        # await asyncio.sleep(generate_random_decimal())
        # await page.get_by_role('link', name='로그인', exact=True).click()
        # await asyncio.sleep(generate_random_decimal())
        # await page.get_by_role('button', name='취소').click()


        #페이지 제목 출력
        #print(f"페이지 제목: {await page.title()}")

        input("종료하시려면 엔터를 눌러주세요 : ")

        # browser를 닫습니다.
        await browser.close()
        
        print("***크롤링을 종료합니다***")