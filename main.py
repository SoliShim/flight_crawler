import asyncio
import random
import datetime
from playwright.async_api import async_playwright;


#랜덤 프로필 만들기#############################################3
def generate_random_profile():
    """
    랜덤 프로필을 생성하는 함수
    """
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
    ]
    
    languages = ['ko-KR', 'en-US', 'ja-JP', 'zh-CN']
    
    timezones = [
        'Asia/Seoul',
        'America/New_York',
        'Europe/London',
        'Asia/Tokyo',
    ]
    
    viewports = [
        {'width': 1500, 'height': 1080},
        {'width': 1366, 'height': 768},
        {'width': 1440, 'height': 900},
        {'width': 1280, 'height': 720},
    ]
    
    return {
        'user_agent': random.choice(user_agents),
        'locale': random.choice(languages),
        'timezone_id': random.choice(timezones),
        'device_scale_factor': random.choice([1, 2]),
        'viewport': random.choice(viewports),
    }

def print_profile_info(profile, iteration=None):
    """
    프로필 정보를 출력하는 함수
    """
    if iteration:
        print(f"\n=== 접속 {iteration} ===")
    print(f"User Agent: {profile['user_agent'][:60]}...")
    print(f"언어: {profile['locale']}")
    print(f"타임존: {profile['timezone_id']}")
    print(f"화면 크기: {profile['viewport']['width']}x{profile['viewport']['height']}")


#랜덤 숫자 만들기################################################

def generate_random_decimal(min_val=0.5, max_val=3.0, decimal_places=4):
    random_float = random.uniform(min_val, max_val)
    return round(random_float, decimal_places)

#YYYY.MM. 함수################################################

def get_today_year_month():
    now = str(datetime.date.today())
    return now[:4]+'.'+now[5:7]+'.'
    #형식 예 2025.05.

#DD 함수################################################

def get_today_day():
    now = str(datetime.date.today())
    return int(now[8:])     #한자리 수가 02 처럼 두자리로 나오면 잘라줌


## 캘린더 안에서 월 찾기#####################################33
async def click_calendar_date(page, target_month, target_day, start_from_visible=True):
    """
    범용 캘린더 날짜 클릭 함수
    
    매개변수:
    - page: Playwright page 객체
    - target_month: '2026.05.' 형식
    - target_day: 날짜 숫자 (예: 23)
    - start_from_visible: True면 현재 보이는 달부터 시작, False면 처음부터 스크롤
    """
    max_scrolls = 50
    scroll_step = 500
    
    print(f"\n[시작] {target_month}{target_day}. 선택...")
    
    container = page.locator('div.sc-dhKdcB.dbuCbp.awesome-calendar')
    await container.scroll_into_view_if_needed()
    
    # 1단계: 현재 보이는 월 찾기
    month_divs = page.locator('div.sc-kpDqfm.DcnuU.month')
    month_count = await month_divs.count()
    
    current_visible_index = 0
    
    if start_from_visible:
        #print(f"[1단계] 현재 보이는 달 찾기...")
        for j in range(month_count):
            month_div = month_divs.nth(j)
            if await month_div.is_visible():
                current_visible_index = j
                #print(f"✓ 현재 보이는 달 인덱스: {current_visible_index}")
                break
    
    # 2단계: 목표 월 찾기 (현재 보이는 위치부터 스크롤 시작)
    #print(f"[2단계] {target_month} 월을 찾기 위해 스크롤 중...")
    
    target_month_div = None
    target_month_index = None
    
    for i in range(max_scrolls):
        # ⭐️ 수정: exact=True 추가 (정확히 일치하는 div.sc-dAlyuH.cKxEnD만 찾기)
        month_text_locator = page.get_by_text(target_month, exact=True)
        
        try:
            if await month_text_locator.first.is_visible():
                #print(f"✓ {target_month} 월 발견!")
                
                # 정확한 month div 찾기
                for j in range(month_count):
                    month_div = month_divs.nth(j)
                    text_in_div = await month_div.get_by_text(target_month, exact=True).count()
                    
                    if text_in_div > 0:
                        #print(f"✓ {target_month} 달력 요소 발견! (인덱스: {j})")
                        target_month_div = month_div
                        target_month_index = j
                        break
                break
        except Exception as e:
            #print(f"[2단계 검색 중] {e}")
            pass
        
        # 아래로 스크롤
        await page.mouse.wheel(0, scroll_step)
        await asyncio.sleep(0.5)
    else:
        #print(f"✗ {target_month} 월을 찾지 못했습니다.")
        return False
    
    if target_month_div is None:
        #print(f"✗ {target_month} 달력 요소를 찾지 못했습니다.")
        return False
    
    # 3단계: 해당 month div를 화면에 보이게 스크롤
    #print(f"[3단계] 인덱스 {target_month_index}의 달력을 화면 중앙에 배치...")
    await target_month_div.scroll_into_view_if_needed()
    await asyncio.sleep(0.5)
    
    # 4단계: 해당 월 안에서 목표 날짜 클릭
    #print(f"[4단계] {target_month}에서 {target_day}일 클릭...")
    
    # 방법 1: get_by_role()과 정규표현식 사용
    try:
        import re
        day_button = target_month_div.get_by_role('button', name=re.compile(f'^{target_day}$'))
        
        if await day_button.count() > 0:
            #print(f"✓ {target_day}일 버튼 발견! (방법 1: role 사용)")
            await day_button.first.scroll_into_view_if_needed()
            await asyncio.sleep(0.3)
            await day_button.first.click()
            #print(f"✓ {target_day}일 버튼 클릭 완료!")
            print(f"✓ 선택 완료!")
            return True
    except Exception as e:
        #print(f"방법 1 실패: {e}")
        pass
    
    # 방법 2: get_by_text()로 정확히 찾기
    try:
        day_button = target_month_div.get_by_text(str(target_day), exact=True)
        
        if await day_button.count() > 0:
            #print(f"✓ {target_day}일 버튼 발견! (방법 2: text 사용)")
            button_element = day_button.first.locator('xpath=ancestor::button[1]')
            
            if await button_element.count() > 0:
                await button_element.scroll_into_view_if_needed()
                await asyncio.sleep(0.3)
                await button_element.click()
                #print(f"✓ {target_day}일 버튼 클릭 완료!")
                print(f"✓ 선택 완료!")
                return True
            else:
                await day_button.first.scroll_into_view_if_needed()
                await asyncio.sleep(0.3)
                await day_button.first.click()
                #print(f"✓ {target_day}일 클릭 완료!")
                print(f"✓ 선택 완료!")
                return True
    except Exception as e:
        #print(f"방법 2 실패: {e}")
        pass
    
    # 방법 3: 마우스 좌표로 직접 클릭
    try:
        #print(f"[4-3단계] 방법 3: 마우스 좌표로 클릭 시도...")
        day_buttons = target_month_div.locator('button.sc-jIIzhew')
        day_count = await day_buttons.count()
        
        for k in range(day_count):
            button = day_buttons.nth(k)
            
            b_element = button.locator('b')
            if await b_element.count() > 0:
                button_text = await b_element.first.text_content()
            else:
                button_text = await button.text_content()
            
            if button_text and button_text.strip() == str(target_day):
                box = await button.bounding_box()
                if box:
                    center_x = box['x'] + box['width'] / 2
                    center_y = box['y'] + box['height'] / 2
                    
                    #print(f"✓ {target_day}일 버튼 발견! (좌표: {center_x}, {center_y})")
                    
                    await page.mouse.move(center_x, center_y)
                    await asyncio.sleep(0.2)
                    await page.mouse.click(center_x, center_y)
                    await asyncio.sleep(0.3)
                    
                    #print(f"✓ {target_day}일 버튼 마우스 클릭 완료!")
                    print(f"✓ 선택 완료!")
                    return True
    except Exception as e:
        #print(f"방법 3 실패: {e}")
        pass
    
    print(f"✗ {target_month}에서 {target_day}일을 클릭하지 못했습니다.")
    return False


################################################################


async def scrape_cau():
    """
    스카이스캐너 사이트를 크롤링하는 함수
    """
    print("스카이스캐너 크롤링을 시작합니다...")
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
        await page.goto("https://mportal2.cau.ac.kr/main.do")
        print("중앙대학교 페이지에 접속했습니다.")


        #요소 찾기 (로케이터)
        await page.get_by_role('link', name='로그인', exact=True).click() #exact=True는 정확히 일치하는 요소를 찾겠다는 의미
        await asyncio.sleep(generate_random_decimal())
        await page.get_by_role('textbox', name='사용자 ID를 입력해주세요.', exact=True).type('solomon1221')
        await asyncio.sleep(generate_random_decimal())
        await page.get_by_role('textbox', name='비밀번호를 입력해주세요.', exact=True).type('solomon3588!')
        await asyncio.sleep(generate_random_decimal())
        await page.get_by_role('link', name='로그인', exact=True).click()
        await asyncio.sleep(generate_random_decimal())
        await page.get_by_role('button', name='취소').click()


        #페이지 제목 출력
        print(f"페이지 제목: {await page.title()}")

        # --- 여기에 크롤링 로직을 추가하세요 ---
        # 예: 출발지/도착지 입력, 날짜 선택, 검색 버튼 클릭, 결과 데이터 파싱 등
        # await page.fill('input[name="fsc-origin-search"]', '서울')
        # await page.click('button[type="submit"]')
        # await page.wait_for_selector('.flight-card')
        # ------------------------------------

        # 예시로 5초간 대기합니다. 실제로는 로직에 맞게 대기 조건을 설정해야 합니다.
        #await asyncio.sleep(5)
        input("종료하시려면 엔터를 눌러주세요 : ")

        # browser를 닫습니다.
        await browser.close()
        
        print("***크롤링을 종료합니다***")


async def scrape_naver():
    """
    네이버 항공권 사이트를 크롤링하는 함수
    """
    print("네이버 항공권 크롤링을 시작합니다...")
    async with async_playwright() as p: 
        #playwright 라이브러리 초기화하고 p라고 하겠다.
        #with는 블록이 끝나면 자동으로 리소스 정리하라는 의미
        profile = generate_random_profile()
        print_profile_info(profile)
        
        browser = await p.chromium.launch(headless=False)
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
        
        #목적지 공항 저장할 변수
        dest3 = 'TPE'

        # 네이버 항공권 웹사이트로 이동합니다.
        await page.goto("https://flight.naver.com/")
        print("네이버 항공권 페이지에 접속했습니다.")
        #페이지 제목 출력
        print(f"페이지 제목: {await page.title()}")



        #요소 찾기 (로케이터)
        await page.get_by_text('도착지', exact=True).click() #exact=True는 정확히 일치하는 요소를 찾겠다는 의미
        await asyncio.sleep(generate_random_decimal())
        
        
        #검색창에 공항 이름 입력하기
        
        dest3 = input("목적지 공항을 입력하세요(IATA 3자리 코드) : ")
        await page.get_by_role('textbox', name='국가, 도시, 공항명 검색').type(dest3)
        await asyncio.sleep(generate_random_decimal())

        #공항 결과가 뜨면 클릭하기
        try : 
            await page.get_by_text(dest3).first.click()
            print("목적지가",dest3,"으로 설정되었습니다.")
        except Exception as e:
            print("목적지가 정상적으로 설정되지 못했습니다.")
            
        await asyncio.sleep(generate_random_decimal())
        


        #가는날 선택, 오는날 선택에 필요한 변수
                
        depyyyymm = get_today_year_month()
        depdd = get_today_day()   #dd는 03 아니고 3으로 표기.
        
        depdate = input("출발 연월일을 입력하세요(ex. 20251102) :")
        depyyyymm = depdate[:4]+'.'+depdate[4:6]+'.'
        depdd = int(depdate[6:])

        #______도착날_______________________
        retyyyymm = depyyyymm
        retdd = depdd+1   #도착날은 

        while(True):
            retdate = input("도착 연월일을 입력하세요(ex. 20251102) :")
            if(depdate<retdate):
                break
            print("다시 입력 해주세요. 복귀일이 출발일보다 빠를 수 없습니다.")
        retyyyymm = retdate[:4]+'.'+retdate[4:6]+'.'
        retdd = int(retdate[6:])

        #가는날 선택    
        await page.get_by_role('button', name='가는 날').click()
        await page.mouse.wheel(0, 700)     #휠 아래로 조금 내리기
        await asyncio.sleep(generate_random_decimal()) 

        await click_calendar_date(page, depyyyymm, depdd, start_from_visible=False) #날짜 선택하는 함수!        
        await asyncio.sleep(generate_random_decimal())

        #오는날 선택
        #arr
        await click_calendar_date(page, retyyyymm, retdd, start_from_visible=True) #날짜 선택하는 함수!    



        await page.get_by_role('button', name='검색').click()







        #await asyncio.sleep(5)
        input("종료하시려면 엔터를 눌러주세요 : ")

        # browser를 닫습니다.
        await browser.close()
        
        print("***크롤링을 종료합니다***")

async def main():
    """
    메인 실행 함수
    """
    # 두 사이트의 크롤링을 순차적으로 실행합니다.
    # 동시에 실행하고 싶다면 asyncio.gather를 사용할 수 있습니다.
    # await asyncio.gather(scrape_skyscanner(), scrape_naver_flights())
    
    #await scrape_cau()  #스카이스캐너 탐색
    await scrape_naver() #네이버항공권 탐색


if __name__ == "__main__":  #이 프로그램이 실행될 때에만
    # asyncio를 사용하여 main 함수를 실행합니다.
    asyncio.run(main())