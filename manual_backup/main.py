import asyncio
import random
import datetime
import pandas as pd
from playwright.async_api import async_playwright, TimeoutError  # TimeoutError import
import re
import os

# 랜덤 프로필 만들기
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
        # --- 5개 추가 ---
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:122.0) Gecko/20100101 Firefox/122.0'
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


#랜덤 숫자 만들기
def generate_random_decimal(min_val=0.5, max_val=3.0, decimal_places=4):
    random_float = random.uniform(min_val, max_val)
    return round(random_float, decimal_places)

# --- 속도 향상을 위한 짧은 딜레이 함수 ---
def generate_random_short_delay(min_val=0.3, max_val=1.2, decimal_places=4):
    """봇 탐지를 피하기 위한 짧고 랜덤한 딜레이 생성"""
    random_float = random.uniform(min_val, max_val)
    return round(random_float, decimal_places)


#YYYY.MM. 함수
def get_today_year_month():
    now = str(datetime.date.today())
    return now[:4]+'.'+now[5:7]+'.'
    #형식 예 2025.05.

#DD 함수
def get_today_day():
    now = str(datetime.date.today())
    return int(now[8:])     #한자리 수가 02 처럼 두자리로 나오면 잘라줌

# --- 날짜 유효성 검사 함수 ---
def is_valid_date(date_string):
    """YYYYMMDD 형식의 문자열이 유효한 날짜인지 확인"""
    if not (len(date_string) == 8 and date_string.isdigit()):
        return False
    try:
        datetime.datetime.strptime(date_string, '%Y%m%d')
        return True
    except ValueError:
        return False

## 캘린더 안에서 월 찾기
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

async def wait_for_flight_results(page):
    """
    항공권 검색 결과 페이지의 로딩을 안정적으로 대기하는 함수
    스피너가 사라지고 -> 첫 번째 항목이 표시되고 -> networkidle 상태가 될 때까지 대기
    """
    print("\n[Wait] 항공권 검색 결과 로딩 중...")
    try:
        # 1. 로딩 스피너(빙글빙글 도는 아이콘)가 사라질 때까지 대기 (최대 30초)
        spinner_locator = page.locator('div[class*="loading"]')
        await spinner_locator.wait_for(state='hidden', timeout=30000)
        print("✓ 로딩 스피너 사라짐")

        # 2. 첫 번째 항공권 아이템이 렌더링될 때까지 대기 (최대 10초)
        first_item_locator = page.locator('div.combination_ConcurrentItemContainer__uUEbl').first
        await first_item_locator.wait_for(state='visible', timeout=10000)
        print("✓ 첫 번째 항공권 아이템 표시됨")

        # 3. (수정) networkidle 대기 (최대 10초) - 백그라운드 요청이 계속될 수 있음
        # 타임아웃 발생 시, 오류로 중단하지 않고 경고만 출력 후 계속 진행
        try:
            await page.wait_for_load_state('networkidle', timeout=10000)
            print("✓ Network Idle 상태 도달")
        except TimeoutError:
            print("⚠ 'networkidle' 대기 시간(10초) 초과. 백그라운드 요청이 계속되고 있을 수 있으나 스크래핑을 진행합니다.")

        # 4. 최종적으로 잠시 대기하여 스크립트 실행 공간 확보
        await asyncio.sleep(1.5) # 3초 -> 1.5초로 단축

    except Exception as e:
        print(f"✗ 항공권 검색 결과 대기 중 오류 발생: {e}")
        await page.screenshot(path='./error_wait_for_results.png')
        print("오류 발생 시점의 스크린샷을 'error_wait_for_results.png'로 저장했습니다.")
        raise # 오류를 상위로 전달하여 스크래핑 중단


async def scrape_flights_native(page):
    """
    방법 1 (권장): Playwright Locator 네이티브 방식으로 스크래핑
    - 수정: 30개 항목을 목표로 순차적 스크롤 및 스크래핑
    """
    print("\n[Scraping - 방법 1: Playwright Native Locators]")
    
    results_list = []
    
    # 1. 모든 항공권 아이템의 부모 컨테이너 로케이터
    all_items_locator = page.locator('div.combination_ConcurrentItemContainer__uUEbl')
    
    # --- 수정: 30개 항목을 목표로 순차적 스크롤 및 스크래핑 ---
    print("스크롤하며 최대 30개 항목을 수집합니다...")
    max_items_to_scrape = 30

    for i in range(max_items_to_scrape):
        data = {}
        try:
            item = all_items_locator.nth(i)
            
            # 항목이 로드되도록 스크롤하고, 화면에 보일 때까지 대기 (최대 5초)
            # 이것이 동적 로딩(무한 스크롤)을 트리거합니다.
            await item.scroll_into_view_if_needed()
            await item.wait_for(state='visible', timeout=5000) 

            # (기존 스크래핑 로직 시작)
            
            # --- 가격 (공통) ---
            price_text_locator = item.locator('.item_num__aKbk4').first
            # 가격 정보가 없는 항목(광고 등)을 건너뛰기 위해 먼저 확인
            if await price_text_locator.count() == 0:
                print(f"--- 항목 {i+1}은 가격 정보가 없어 건너뜁니다. (광고 예상) ---")
                continue

            price_text = await price_text_locator.inner_text()
            data['price'] = int(price_text.replace(',', ''))
            
            # --- 항공사/경로 (2가지 케이스 분리) ---
            same_airline_block = item.locator('.combination_RoundSameAL__RYbYO')
            diff_airline_blocks = item.locator('.RoundDiffAL')

            if await same_airline_block.count() > 0:
                # === 케이스 1: 왕복 동일 항공사 ===
                data['airline_type'] = 'Same'
                data['airline'] = await same_airline_block.locator('.airline_name__0Tw5w').first.inner_text()
                
                routes = same_airline_block.locator('.route_Route__HYsDn')
                
                # 가는 편
                out_route = routes.nth(0)
                data['outbound_dep_time'] = await out_route.locator('.route_time__xWu7a').nth(0).inner_text()
                data['outbound_dep_code'] = await out_route.locator('.route_code__S07WE').nth(0).inner_text()
                data['outbound_arr_time'] = await out_route.locator('.route_time__xWu7a').nth(1).inner_text()
                data['outbound_arr_code'] = await out_route.locator('.route_code__S07WE').nth(1).inner_text()
                data['outbound_info'] = await out_route.locator('.route_details__F_ShG').first.inner_text()
                
                # 오는 편
                in_route = routes.nth(1)
                data['inbound_dep_time'] = await in_route.locator('.route_time__xWu7a').nth(0).inner_text()
                data['inbound_dep_code'] = await in_route.locator('.route_code__S07WE').nth(0).inner_text()
                data['inbound_arr_time'] = await in_route.locator('.route_time__xWu7a').nth(1).inner_text()
                data['inbound_arr_code'] = await in_route.locator('.route_code__S07WE').nth(1).inner_text()
                data['inbound_info'] = await in_route.locator('.route_details__F_ShG').first.inner_text()

            elif await diff_airline_blocks.count() > 0:
                # === 케이스 2: 왕복 다른 항공사 ===
                data['airline_type'] = 'Different'
                
                # 가는 편
                out_block = diff_airline_blocks.nth(0)
                data['outbound_airline'] = await out_block.locator('.airline_name__0Tw5w').first.inner_text()
                out_route = out_block.locator('.route_Route__HYsDn').first
                data['outbound_dep_time'] = await out_route.locator('.route_time__xWu7a').nth(0).inner_text()
                data['outbound_dep_code'] = await out_route.locator('.route_code__S07WE').nth(0).inner_text()
                data['outbound_arr_time'] = await out_route.locator('.route_time__xWu7a').nth(1).inner_text()
                data['outbound_arr_code'] = await out_route.locator('.route_code__S07WE').nth(1).inner_text()
                data['outbound_info'] = await out_route.locator('.route_details__F_ShG').first.inner_text()
                
                # 오는 편
                in_block = diff_airline_blocks.nth(1)
                data['inbound_airline'] = await in_block.locator('.airline_name__0Tw5w').first.inner_text()
                in_route = in_block.locator('.route_Route__HYsDn').first
                data['inbound_dep_time'] = await in_route.locator('.route_time__xWu7a').nth(0).inner_text()
                data['inbound_dep_code'] = await in_route.locator('.route_code__S07WE').nth(0).inner_text()
                data['inbound_arr_time'] = await in_route.locator('.route_time__xWu7a').nth(1).inner_text()
                data['inbound_arr_code'] = await in_route.locator('.route_code__S07WE').nth(1).inner_text()
                data['inbound_info'] = await in_route.locator('.route_details__F_ShG').first.inner_text()

                # 공통 'airline' 필드 생성
                data['airline'] = f"[왕복다름] {data['outbound_airline']} / {data['inbound_airline']}"
            
            results_list.append(data)
            print(f"✓ 항목 {len(results_list)}/{max_items_to_scrape} 수집 완료: {data.get('airline', 'N/A')} - {data.get('price', 0)}원")

        except TimeoutError:
            # 5초 이내에 nth(i) 항목이 로드되지 않으면,
            # 더 이상 항목이 없는 것(검색 결과가 30개 미만)으로 간주하고 중단.
            print(f"--- {i+1}번째 항목을 로드하지 못했습니다. (총 {len(results_list)}개 수집 후) 스크래핑을 중단합니다. ---")
            break # for 루프 탈출
        
        except Exception as e:
            # 기타 스크래핑 오류 (예: inner_text 실패)
            print(f"--- 항목 {i+1} 스크래핑 중 오류 (건너뜀): {e} ---")
            # print(await item.inner_html()) # 디버깅 시 주석 해제
            print("---------------------------------")
            
    print(f"✅ 총 {len(results_list)}개 항목 스크래핑 성공.")
    df = pd.DataFrame(results_list)
    return df


async def scrape_flights_evaluate_fixed(page):
    """
    방법 2: page.evaluate() 방식 수정
    - 수정: 스크롤 다운 로직을 포함하여 최대 30개 항목 수집
    """
    print("\n[Scraping - 방법 2: page.evaluate() 수정]")
    
    # page.evaluate() 내부에서 사용할 헬퍼 함수 정의
    # (주의: 이 함수는 브라우저 컨텍스트에서 실행되므로 Python 변수/함수 접근 불가)
    scroll_and_scrape_script = """
    async () => {
        const results = [];
        const itemSelector = 'div.combination_ConcurrentItemContainer__uUEbl';
        const maxItems = 30;
        let retries = 5; // 스크롤해도 새 항목이 로드되지 않을 경우를 대비한 안전 장치
        let lastHeight = 0;
        let processedIndex = 0; // 이미 처리한 항목의 인덱스

        const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));

        while (results.length < maxItems) {
            const items = document.querySelectorAll(itemSelector);

            if (items.length === processedIndex && items.length > 0) {
                // 스크롤했는데 새 항목이 로드되지 않음
                retries--;
                if (retries <= 0) {
                    console.warn("No new items loaded after scrolling. Stopping.");
                    break;
                }
                console.log(`No new items, retries left: ${retries}`);
            } else {
                retries = 5; // 새 항목이 로드되었으므로 재시도 횟수 초기화
            }

            // 새로 로드된 항목만 처리
            while (processedIndex < items.length && results.length < maxItems) {
                const item = items[processedIndex];
                try {
                    const data = {};
                    
                    // --- 가격 (공통) ---
                    const priceElem = item.querySelector('.item_num__aKbk4');
                    if (priceElem) {
                        const priceText = priceElem.innerText.replace(/,/g, '').trim();
                        data.price = parseInt(priceText, 10) || 0;
                    } else {
                        // 가격 정보가 없는 아이템(광고 등)은 건너뜀
                        processedIndex++;
                        continue; 
                    }

                    // --- 항공사/경로 (케이스 분리) ---
                    const sameAirlineBlock = item.querySelector('.combination_RoundSameAL__RYbYO');
                    const diffAirlineBlocks = item.querySelectorAll('.RoundDiffAL');

                    if (sameAirlineBlock) {
                        // === 케이스 1: 왕복 동일 항공사 ===
                        data.airline_type = 'Same';
                        const airlineElem = sameAirlineBlock.querySelector('.airline_name__0Tw5w');
                        data.airline = airlineElem ? airlineElem.innerText.trim() : 'N/A';
                        
                        const routes = sameAirlineBlock.querySelectorAll('.route_Route__HYsDn');
                        
                        // 가는 편
                        if (routes[0]) {
                            const times = routes[0].querySelectorAll('.route_time__xWu7a');
                            const codes = routes[0].querySelectorAll('.route_code__S07WE');
                            data.outbound_dep_time = times[0]?.innerText.trim() || '';
                            data.outbound_arr_time = times[1]?.innerText.trim() || '';
                            data.outbound_dep_code = codes[0]?.innerText.trim() || '';
                            data.outbound_arr_code = codes[1]?.innerText.trim() || '';
                            data.outbound_info = routes[0].querySelector('.route_details__F_ShG')?.innerText.trim() || '';
                        }
                        
                        // 오는 편
                        if (routes[1]) {
                            const times = routes[1].querySelectorAll('.route_time__xWu7a');
                            const codes = routes[1].querySelectorAll('.route_code__S07WE');
                            data.inbound_dep_time = times[0]?.innerText.trim() || '';
                            data.inbound_arr_time = times[1]?.innerText.trim() || '';
                            data.inbound_dep_code = codes[0]?.innerText.trim() || '';
                            data.inbound_arr_code = codes[1]?.innerText.trim() || '';
                            data.inbound_info = routes[1].querySelector('.route_details__F_ShG')?.innerText.trim() || '';
                        }
                        
                    } else if (diffAirlineBlocks.length > 0) {
                        // === 케이스 2: 왕복 다른 항공사 ===
                        data.airline_type = 'Different';
                        
                        if (diffAirlineBlocks[0]) {
                            data.outbound_airline = diffAirlineBlocks[0].querySelector('.airline_name__0Tw5w')?.innerText.trim() || 'N/A';
                            const out_route = diffAirlineBlocks[0].querySelector('.route_Route__HYsDn');
                            if (out_route) {
                                data.outbound_dep_time = out_route.querySelectorAll('.route_time__xWu7a')[0]?.innerText.trim() || '';
                                data.outbound_arr_time = out_route.querySelectorAll('.route_time__xWu7a')[1]?.innerText.trim() || '';
                                data.outbound_dep_code = out_route.querySelectorAll('.route_code__S07WE')[0]?.innerText.trim() || '';
                                data.outbound_arr_code = out_route.querySelectorAll('.route_code__S07WE')[1]?.innerText.trim() || '';
                                data.outbound_info = out_route.querySelector('.route_details__F_ShG')?.innerText.trim() || '';
                            }
                        }
                        if (diffAirlineBlocks[1]) {
                            data.inbound_airline = diffAirlineBlocks[1].querySelector('.airline_name__0Tw5w')?.innerText.trim() || 'N/A';
                            const in_route = diffAirlineBlocks[1].querySelector('.route_Route__HYsDn');
                             if (in_route) {
                                data.inbound_dep_time = in_route.querySelectorAll('.route_time__xWu7a')[0]?.innerText.trim() || '';
                                data.inbound_arr_time = in_route.querySelectorAll('.route_time__xWu7a')[1]?.innerText.trim() || '';
                                data.inbound_dep_code = in_route.querySelectorAll('.route_code__S07WE')[0]?.innerText.trim() || '';
                                data.inbound_arr_code = in_route.querySelectorAll('.route_code__S07WE')[1]?.innerText.trim() || '';
                                data.inbound_info = in_route.querySelector('.route_details__F_ShG')?.innerText.trim() || '';
                            }
                        }
                        data.airline = `[왕복다름] ${data.outbound_airline || 'N/A'} / ${data.inbound_airline || 'N/A'}`;
                    }

                    results.push(data);
                    console.log(`✓ Item ${results.length}/${maxItems} collected: ${data.airline} - ${data.price}원`);

                } catch (e) {
                    console.error(`Error at item index ${processedIndex}:`, e.message);
                }
                processedIndex++; // 다음 항목으로 이동
            } // end while(processedIndex < items.length)

            if (results.length >= maxItems) {
                break; // 목표 달성
            }

            // 다음 항목을 로드하기 위해 스크롤
            lastHeight = document.documentElement.scrollHeight;
            window.scrollTo(0, lastHeight);
            
            // 새 콘텐츠가 로드될 시간을 줍니다.
            await delay(1000); 

        } // end while(results.length < maxItems)
        
        console.log(`=== 총 ${results.length}개 항공권 추출 완료 ===`);
        return results;
    }
    """
    
    # page.evaluate()의 기본 타임아웃(30초)을 늘려줍니다. (스크롤 및 대기 시간 포함)
    # 30개 * (스크롤 대기 1초) = 최소 30초 + @
    flights_data = await page.evaluate(scroll_and_scrape_script, timeout=90000)
    
    print(f"\n✅ JavaScript 추출 완료: {len(flights_data)}개")
    df = pd.DataFrame(flights_data)
    return df

##############################################################################

async def scrape_cau():
    """
    중앙대학교 사이트를 크롤링하는 함수
    """
    print("중앙대학교 크롤링을 시작합니다...")
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
        await page.get_by_role('textbox', name='사용자 ID를 입력해주세요.', exact=True).type('')
        await asyncio.sleep(generate_random_decimal())
        await page.get_by_role('textbox', name='비밀번호를 입력해주세요.', exact=True).type('')
        await asyncio.sleep(generate_random_decimal())
        await page.get_by_role('link', name='로그인', exact=True).click()
        await asyncio.sleep(generate_random_decimal())
        await page.get_by_role('button', name='취소').click()


        #페이지 제목 출력
        print(f"페이지 제목: {await page.title()}")

        input("종료하시려면 엔터를 눌러주세요 : ")

        # browser를 닫습니다.
        await browser.close()
        
        print("***크롤링을 종료합니다***")

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

async def scrape_naver():
    """
    네이버 항공권 사이트를 크롤링하는 함수
    """
    print("네이버 항공권 크롤링을 시작합니다...")
    async with async_playwright() as p: 

        #@@@ 변수 선언파트@@@@@@@@@@@@@@@@@@@@@@@@
        
        # 오늘 날짜 기준으로 기본값 설정
        today = datetime.date.today()
        default_dep_date = today + datetime.timedelta(days=1)
        default_ret_date = today + datetime.timedelta(days=2)

        depyyyymm = default_dep_date.strftime('%Y.%m.')
        depdd = default_dep_date.day
        retyyyymm = default_ret_date.strftime('%Y.%m.')
        retdd = default_ret_date.day
        
        arr3_default = 'TPE'
        depdate_default_str = default_dep_date.strftime('%Y%m%d')
        retdate_default_str = default_ret_date.strftime('%Y%m%d')


        #입력받기_________________(입력 필요 없으면 전체 주석처리)___________________________

        ##공항 선택
        while True:
            arr3 = input(f"목적지 공항을 입력하세요(IATA 3자리 코드, 예: {arr3_default}) : ")
            if not arr3: # 엔터만 치면 기본값 사용
                arr3 = arr3_default
                print(f"기본값 {arr3}을 사용합니다.")
                break
            
            arr3 = arr3.upper() # 소문자를 대문자로
            if arr3.isalpha() and len(arr3) == 3:
                break
            print("✗ 잘못된 형식입니다. 반드시 알파벳 3자리로 입력해주세요.")

        ##출발일 선택
        while True:
            depdate = input(f"출발 연월일을 입력하세요(YYYYMMDD, 예: {depdate_default_str}) :")
            if not depdate:
                depdate = depdate_default_str
                print(f"기본값 {depdate}를 사용합니다.")
                break
            if is_valid_date(depdate):
                break
            print("✗ 잘못된 날짜 형식입니다. YYYYMMDD (예: 20251104) 8자리 숫자로 올바르게 입력해주세요.")

        #도착일 선택
        while True:
            retdate = input(f"도착 연월일을 입력하세요(YYYYMMDD, 예: {retdate_default_str}) :")
            if not retdate:
                retdate = retdate_default_str
                print(f"기본값 {retdate}를 사용합니다.")
            
            if not is_valid_date(retdate):
                print("✗ 잘못된 날짜 형식입니다. YYYYMMDD 8자리 숫자로 올바르게 입력해주세요.")
                continue
                
            if depdate < retdate:
                break
            print("✗ 다시 입력 해주세요. 복귀일이 출발일보다 빠르거나 같을 수 없습니다.")

        # 입력값을 날짜 형식 변수로 변환
        depyyyymm = depdate[:4]+'.'+depdate[4:6]+'.'
        depdd = int(depdate[6:])
        retyyyymm = retdate[:4]+'.'+retdate[4:6]+'.'
        retdd = int(retdate[6:])
        
        #___________입력 끝_____________________________________________________________________________



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


        # 네이버 항공권 웹사이트로 이동합니다.
        await page.goto("https://flight.naver.com/")
        print("네이버 항공권 페이지에 접속했습니다.")
        #페이지 제목 출력
        print(f"페이지 제목: {await page.title()}")

        #~~~~~~~광고 나오면 닫기 시도~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        try:
            # 시도 1: '오늘 하루 보지 않기' 등 텍스트 기반 닫기 버튼
            # 특정 클래스 이름 대신 텍스트로 찾는 것이 더 견고할 수 있음
            close_popup_button = page.get_by_role("button", name=re.compile("오늘 하루 보지 않기|다시 보지 않기|7일간 보지 않기|닫기"))
            if await close_popup_button.count() > 0:
                await close_popup_button.first.click(timeout=3000)
                print("✓ 텍스트 기반 팝업 닫기 버튼 클릭")
            else:
                 # 시도 2: 'x' 또는 'close' 포함하는 버튼 (aria-label 등)
                close_icon_button = page.locator("button[class*='close'], button[aria-label*='닫기'], button[aria-label*='close']")
                if await close_icon_button.count() > 0:
                    await close_icon_button.first.click(timeout=3000)
                    print("✓ 아이콘(X) 팝업 닫기 버튼 클릭")
                else:
                    print("... 광고 팝업이 발견되지 않았거나, 다른 유형의 팝업입니다.")
            
            await page.wait_for_timeout(500) # 닫기 후 잠시 대기

        except Exception as e:
            print(f"--- 광고 팝업 닫기 중 예외 발생 (무시하고 계속): {e} ---")
        #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~



        #요소 찾기 (로케이터)
        await page.get_by_text('도착지', exact=True).click() #exact=True는 정확히 일치하는 요소를 찾겠다는 의미
        await asyncio.sleep(generate_random_short_delay())
        
        
        #검색창에 공항 이름 입력하기
                
        await page.get_by_role('textbox', name='국가, 도시, 공항명 검색').type(arr3)
        await asyncio.sleep(generate_random_short_delay())

        #공항 결과가 뜨면 클릭하기
        try:
            # 결과 리스트의 모든 <a> 태그 중 텍스트(공항 코드)가 arr3인 것 찾기
            anchors = page.locator('a.searchResults_anchor__OXs_5')
            count = await anchors.count()
            clicked = False

            if count == 0:
                 print(f"--- {arr3} 검색 결과가 없습니다. (잠시 대기 후 재시도) ---")
                 await asyncio.sleep(1.5) # 딜레이를 조금 더 줌
                 count = await anchors.count()

            for i in range(count):
                anchor = anchors.nth(i)
                # <b> 안에 arr3이 들어있는지 확인 (예: NRT, TPE 등)
                anchor_text = await anchor.inner_text()
                if anchor_text and arr3 in anchor_text.split(): # TPE (타오위안) 같은 형식
                    await anchor.scroll_into_view_if_needed()
                    await anchor.click()
                    clicked = True
                    print(f"✓ 목적지가 {arr3} ({anchor_text.splitlines()[0]}) (으)로 설정되었습니다.")
                    break

            if not clicked:
                print(f"✗ {arr3}에 해당하는 목적지를 클릭하지 못했습니다.")

        except Exception as e:
            print(f"✗ 목적지 설정 중 오류 발생: {e}")

            
        await asyncio.sleep(generate_random_short_delay())
        


        #____playwright에서 마우스로 선택_________________________________________________________________
        #가는날 선택      
        await page.get_by_role('button', name='가는 날').click()
        await page.mouse.wheel(0, 700)      #휠 아래로 조금 내리기
        await asyncio.sleep(generate_random_short_delay()) 

        await click_calendar_date(page, depyyyymm, depdd, start_from_visible=False) #날짜 선택하는 함수!       
        await asyncio.sleep(generate_random_short_delay())

        #오는날 선택
        await click_calendar_date(page, retyyyymm, retdd, start_from_visible=True) #날짜 선택하는 함수!   

        #검색버튼 누르기
        # --- 수정: '검색' 이름의 버튼이 2개 발견되는 오류(strict mode violation) 해결 ---
        await page.get_by_role('button', name='검색', exact=True).click()

        # --- 중요: 여기가 수정된 부분 ---
        # 고정 대기(sleep) 대신, 결과가 로드될 때까지 '명시적 대기'
        await wait_for_flight_results(page)
        # -------------------------------


        #검색결과 df로 저장 시도

        # --- 방법 1 (권장) ---
        saved_info = await scrape_flights_native(page)
        
        # --- 방법 2 (수정된 evaluate) ---
        # saved_info = await scrape_flights_evaluate_fixed(page)


        print("\n--- 최종 결과 (상위 5개) ---")
        print(saved_info.head())
        print("--------------------------\n")

        # --- 결과 저장 ---
        # 폴더 생성
        os.makedirs('./result', exist_ok=True)
        
        # 파일명 생성
        screenshot_filename = f'./result/SEL_TO_{arr3}_{depdate}-{retdate}.png'
        excel_filename = f'./result/SEL_TO_{arr3}_{depdate}-{retdate}.xlsx'

        #검색결과 스크린샷
        await page.screenshot(path=screenshot_filename, full_page=True)
        print(f"✓ 검색결과가 스크린샷으로 저장되었습니다. ({screenshot_filename})")

        # 엑셀로 저장
        saved_info.to_excel(excel_filename, index=False)
        print(f"✓ 검색결과가 Excel 파일로 저장되었습니다. ({excel_filename})")


        print("\n\n이용해주셔서 감사합니다 :)")
        await asyncio.sleep(5)
        
        # input("슬퍼요ㅜㅜㅜ") # 디버깅 완료 후 주석 처리 권장
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
    
    #await scrape_cau() 
    await scrape_naver() #네이버항공권 탐색
    #await scrape_google_flight() 




if __name__ == "__main__":  #이 프로그램이 실행될 때에만
    # asyncio를 사용하여 main 함수를 실행합니다.
    asyncio.run(main())

