import asyncio
import datetime
import pandas as pd
from playwright.async_api import async_playwright, TimeoutError
import re
import os
from utils import is_valid_date, generate_random_profile, print_profile_info, generate_random_short_delay


RESULT_ITEM_SELECTOR = 'div.combination_ConcurrentItemContainer__uUEbl'
RESULT_PRICE_SELECTOR = '.item_num__aKbk4'


def output_date_suffix(depdate, retdate, trip_type):
    return f"{depdate}-oneway" if trip_type == "oneway" else f"{depdate}-{retdate}"


##검색창에 공항 이름 입력하기
async def insert_airport(page, airport3, label="공항"):
    await close_ad_popup_if_present(page)
    search_box = page.get_by_role('textbox', name='국가, 도시, 공항명 검색').first
    await search_box.wait_for(state='visible', timeout=10000)
    await search_box.fill("")
    await search_box.type(airport3)
    await asyncio.sleep(generate_random_short_delay())

    #공항 결과가 뜨면 클릭하기
    try:
        # 결과 리스트의 모든 <a> 태그 중 텍스트(공항 코드)가 arr3인 것 찾기
        anchors = page.locator('a[class*="searchResults_anchor"]')
        try:
            await anchors.first.wait_for(state='visible', timeout=5000)
        except TimeoutError:
            pass
        count = await anchors.count()
        clicked = False

        if count == 0:
             print(f"--- {airport3} 검색 결과가 없습니다. (잠시 대기 후 재시도) ---")
             await asyncio.sleep(1.5) # 딜레이를 조금 더 줌
             count = await anchors.count()

        for i in range(count):
            anchor = anchors.nth(i)
            # <b> 안에 arr3이 들어있는지 확인 (예: NRT, TPE 등)
            anchor_text = await anchor.inner_text()
            if anchor_text and airport3 in anchor_text.split(): # TPE (타오위안) 같은 형식
                await anchor.scroll_into_view_if_needed()
                await anchor.click()
                clicked = True
                print(f"✓ {label}가 {airport3} ({anchor_text.splitlines()[0]}) (으)로 설정되었습니다.")
                break

        if not clicked:
            fallback = page.get_by_text(re.compile(rf"\b{re.escape(airport3)}\b")).first
            if await fallback.count() > 0 and await fallback.is_visible():
                link = fallback.locator("xpath=ancestor::a[1]")
                if await link.count() > 0:
                    await link.click()
                else:
                    await fallback.click()
                clicked = True
                print(f"✓ {label}가 {airport3} (으)로 설정되었습니다.")

        if not clicked:
            print(f"✗ {airport3}에 해당하는 {label}를 클릭하지 못했습니다.")
            return False

    except Exception as e:
        print(f"✗ {label} 설정 중 오류 발생: {e}")
        return False
    await asyncio.sleep(generate_random_short_delay())
    return clicked


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
    
    
    if start_from_visible:
        #print(f"[1단계] 현재 보이는 달 찾기...")
        for j in range(month_count):
            month_div = month_divs.nth(j)
            if await month_div.is_visible():
                #print(f"✓ 현재 보이는 달 인덱스: {current_visible_index}")
                break
    
    # 2단계: 목표 월 찾기 (현재 보이는 위치부터 스크롤 시작)
    #print(f"[2단계] {target_month} 월을 찾기 위해 스크롤 중...")
    
    target_month_div = None
    
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

async def get_result_snapshot(page):
    """
    현재 렌더링된 항공권 결과 상태를 요약합니다.
    네이버가 비동기로 가격/정렬을 갱신할 수 있으므로 count와 가격 fingerprint를 같이 봅니다.
    """
    return await page.evaluate(
        """
        ({ itemSelector, priceSelector }) => {
            const items = Array.from(document.querySelectorAll(itemSelector));
            const prices = items
                .map((item) => item.querySelector(priceSelector)?.innerText?.trim() || "")
                .filter(Boolean);

            return {
                itemCount: items.length,
                pricedItemCount: prices.length,
                firstPrice: prices[0] || "",
                fingerprint: `${items.length}::${prices.slice(0, 30).join("|")}`,
            };
        }
        """,
        {
            "itemSelector": RESULT_ITEM_SELECTOR,
            "priceSelector": RESULT_PRICE_SELECTOR,
        },
    )


async def wait_for_result_stability(
    page,
    min_wait_seconds=5.0,
    stable_seconds=2.5,
    max_wait_seconds=20.0,
    interval_seconds=0.5,
):
    """
    검색 결과가 일정 시간 동안 변하지 않을 때까지 기다립니다.
    고정 sleep 대신 DOM에 표시된 항공권 개수와 상위 가격 목록을 기준으로 안정화를 판단합니다.
    """
    print(
        f"... (3/3) 결과 안정화 대기 중 "
        f"(최소 {min_wait_seconds:.0f}초, 최대 {max_wait_seconds:.0f}초)"
    )

    loop = asyncio.get_running_loop()
    started_at = loop.time()
    last_changed_at = started_at
    last_fingerprint = None
    last_snapshot = None
    checkpoints = [3, 5, 7, 10, 15, 20]
    printed_checkpoints = set()

    while True:
        now = loop.time()
        elapsed = now - started_at
        snapshot = await get_result_snapshot(page)
        fingerprint = snapshot["fingerprint"]

        if fingerprint != last_fingerprint:
            last_fingerprint = fingerprint
            last_changed_at = now
            last_snapshot = snapshot

        for checkpoint in checkpoints:
            if elapsed >= checkpoint and checkpoint not in printed_checkpoints:
                printed_checkpoints.add(checkpoint)
                print(
                    f"... {checkpoint}초 경과: "
                    f"결과 {snapshot['itemCount']}개, "
                    f"가격 표시 {snapshot['pricedItemCount']}개, "
                    f"첫 가격 {snapshot['firstPrice'] or 'N/A'}"
                )

        stable_for = now - last_changed_at
        has_prices = snapshot["pricedItemCount"] > 0
        if elapsed >= min_wait_seconds and stable_for >= stable_seconds and has_prices:
            print(
                f"✓ 결과 안정화 완료: "
                f"{snapshot['pricedItemCount']}개 가격 표시, "
                f"{elapsed:.1f}초 대기"
            )
            return last_snapshot or snapshot

        if elapsed >= max_wait_seconds:
            print(
                f"⚠ 최대 대기 시간 도달: "
                f"{snapshot['pricedItemCount']}개 가격 표시 상태로 진행"
            )
            return snapshot

        await asyncio.sleep(interval_seconds)


#기다려!
async def wait_for_flight_results(page):
    """
    항공권 검색 결과 페이지의 로딩을 안정적으로 대기하는 함수 (속도 최적화 버전)
    [수정] 스피너가 사라지고 -> 첫 번째 항목이 '표시'되는 즉시 다음 단계로 진행합니다.
    'networkidle' 대기 및 추가 sleep을 제거하여 속도를 향상시킵니다.
    """
    print("\n[Wait] 항공권 검색 결과 로딩 중... (속도 최적화 버전)")
    try:
        # 1. 로딩 스피너(빙글빙글 도는 아이콘)가 사라질 때까지 대기 (최대 30초)
        #    이것은 페이지가 최소한의 응답을 하고 로딩을 시작했다는 신호입니다.
        spinner_locator = page.locator('div[class*="loading"]')
        print("... (1/3) 로딩 스피너 사라지기를 대기 중 (최대 30초)")
        await spinner_locator.wait_for(state='hidden', timeout=30000)
        print("✓ (1/3) 로딩 스피너 사라짐")

        # 2. 첫 번째 항공권 아이템이 렌더링될 때까지 대기 (최대 30초)
        #    이것이 스크래핑을 시작할 수 있는 '가장 중요한 신호'입니다.
        #    (기존 10초에서 15초로 약간 여유를 주어 네트워크 환경 대응)
        first_item_locator = page.locator(RESULT_ITEM_SELECTOR).first
        print("... (2/3) 첫 번째 항공권 아이템 표시 대기 중 (최대 30초)")
        await first_item_locator.wait_for(state='visible', timeout=30000)
        print("✓ (2/3) 첫 번째 항공권 아이템 표시됨.")

        min_wait_seconds = float(os.getenv("NAVER_RESULT_MIN_WAIT_SECONDS", "5"))
        stable_seconds = float(os.getenv("NAVER_RESULT_STABLE_SECONDS", "2.5"))
        max_wait_seconds = float(os.getenv("NAVER_RESULT_MAX_WAIT_SECONDS", "20"))
        await wait_for_result_stability(
            page,
            min_wait_seconds=min_wait_seconds,
            stable_seconds=stable_seconds,
            max_wait_seconds=max_wait_seconds,
        )

    except TimeoutError as e:
        # 타임아웃 오류를 좀 더 명확하게 구분
        print(f"✗ 항공권 검색 결과 대기 중 시간 초과: {e}")
        await page.screenshot(path='./error_wait_for_results_timeout.png')
        print("오류 발생 시점의 스크린샷을 'error_wait_for_results_timeout.png'로 저장했습니다.")
        raise # 오류를 상위로 전달하여 스크래핑 중단
        
    except Exception as e:
        print(f"✗ 항공권 검색 결과 대기 중 알 수 없는 오류 발생: {e}")
        await page.screenshot(path='./error_wait_for_results_exception.png')
        print("오류 발생 시점의 스크린샷을 'error_wait_for_results_exception.png'로 저장했습니다.")
        raise # 오류를 상위로 전달하여 스크래핑 중단


async def close_ad_popup_if_present(page):
    """
    네이버 항공권의 광고/안내 팝업이 화면을 덮으면 닫습니다.
    페이지 안에는 숨겨진 닫기 버튼도 많아서, 실제 팝업 영역 안의 보이는 요소만 클릭합니다.
    """
    popup = page.locator("#ad-popup")
    try:
        if await popup.count() == 0:
            print("... 광고 팝업이 발견되지 않았습니다.")
            return
    except Exception:
        print("... 광고 팝업이 발견되지 않았습니다.")
        return

    close_text = re.compile("오늘 하루 보지 않기|다시 보지 않기|7일간 보지 않기|닫기|close", re.IGNORECASE)
    candidates = popup.locator("button, a, [role='button']").filter(has_text=close_text)

    try:
        count = await candidates.count()
        for i in range(count):
            button = candidates.nth(i)
            if await button.is_visible():
                await button.click(timeout=3000)
                print("✓ 광고 팝업 닫기 버튼 클릭")
                await page.wait_for_timeout(500)
                return

        visible_controls = popup.locator("button, a, [role='button']")
        count = await visible_controls.count()
        for i in range(count - 1, -1, -1):
            button = visible_controls.nth(i)
            if await button.is_visible():
                await button.click(timeout=3000)
                print("✓ 광고 팝업의 보이는 버튼을 클릭해 닫기 시도")
                await page.wait_for_timeout(500)
                return
    except Exception as e:
        print(f"--- 광고 팝업 닫기 중 예외 발생 (무시하고 계속): {e} ---")

    try:
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(500)
        if await popup.count() > 0:
            await popup.first.evaluate("element => element.remove()")
            print("✓ 광고 팝업 레이어를 제거했습니다.")
    except Exception as e:
        print(f"--- 광고 팝업 fallback 처리 중 예외 발생 (무시하고 계속): {e} ---")


async def select_naver_trip_type(page, trip_type):
    if trip_type != "oneway":
        return

    print("... 네이버 항공권 여정 방식을 편도로 설정 중")
    candidates = [
        page.get_by_role("button", name="편도", exact=True),
        page.get_by_text("편도", exact=True),
    ]
    for candidate in candidates:
        try:
            if await candidate.count() > 0:
                await candidate.first.click(timeout=3000)
                await page.wait_for_timeout(500)
                print("✓ 네이버 항공권 편도 설정 완료")
                return
        except Exception:
            pass

    raise RuntimeError("네이버 항공권 편도 버튼을 찾지 못했습니다.")


#항공권 결과 수집
async def scrape_flights_hybrid(page, max_items_to_scrape=30):
    """
    page.evaluate()로 현재 렌더링된 항공권 목록을 읽고, 새 항목 로드를 짧게 대기합니다.
    """
    print(f"\n[Scraping - 방법 3: Hybrid (JS + Smart Wait)] (목표: {max_items_to_scrape}개)")

    # (A) 브라우저에서 실행할 JavaScript 코드 ("설명서")
    scroll_and_scrape_script_hybrid = '''
    async (maxItems) => {
        const results = [];
        const itemSelector = 'div.combination_ConcurrentItemContainer__uUEbl';
        let processedIndex = 0;

        // (B) "똑똑한 대기" 헬퍼 함수
        // (Python의 `item.wait_for('visible')`과 유사한 역할)
        // 현재 항목 개수(currentCount)보다 많아질 때까지 0.1초마다 확인합니다.
        const waitForNewItem = (selector, currentCount) => {
            return new Promise((resolve, reject) => {
                let attempts = 50; // 50 * 100ms = 5초 타임아웃
                const interval = setInterval(() => {
                    const newCount = document.querySelectorAll(selector).length;
                    
                    if (newCount > currentCount) {
                        // (C) 새 항목 발견!
                        clearInterval(interval);
                        resolve(); // 대기 종료
                    }
                    
                    attempts--;
                    if (attempts <= 0) {
                        // (D) 5초간 새 항목이 로드되지 않음 (타임아웃)
                        clearInterval(interval);
                        reject(new Error("Timeout: No new items loaded after 5s."));
                    }
                }, 100); // 0.1초마다 확인
            });
        };

        // (E) 메인 루프 (목표 개수만큼 반복)
        while (results.length < maxItems) {
            
            // (F) 현재 DOM에 로드된 모든 항목을 가져옵니다.
            const items = document.querySelectorAll(itemSelector);

            // (G) 새로 로드된 항목들만 순회합니다.
            while (processedIndex < items.length && results.length < maxItems) {
                const item = items[processedIndex];
                try {
                    const data = {};
                    
                    // --- 가격 (공통) ---
                    const priceElem = item.querySelector('.item_num__aKbk4');
                    if (priceElem) {
                        data.price = parseInt(priceElem.innerText.replace(/,/g, ''), 10);
                    } else {
                        processedIndex++;
                        continue; // 가격 없는 항목(광고) 건너뛰기
                    }
                    const bookingLink = item.querySelector('a[href]') || item.closest('a[href]');
                    data.booking_url = bookingLink
                        ? new URL(bookingLink.getAttribute('href'), window.location.href).href
                        : window.location.href;
                    
                    // --- (방법 2와 동일한 스크래핑 로직) ---
                    const sameAirlineBlock = item.querySelector('.combination_RoundSameAL__RYbYO');
                    const diffAirlineBlocks = item.querySelectorAll('.RoundDiffAL');

                    if (sameAirlineBlock) {
                        data.airline_type = 'Same';
                        data.airline = sameAirlineBlock.querySelector('.airline_name__0Tw5w')?.innerText.trim() || 'N/A';
                        const routes = sameAirlineBlock.querySelectorAll('.route_Route__HYsDn');
                        if (routes[0]) {
                            data.outbound_dep_time = routes[0].querySelectorAll('.route_time__xWu7a')[0]?.innerText.trim() || '';
                            data.outbound_arr_time = routes[0].querySelectorAll('.route_time__xWu7a')[1]?.innerText.trim() || '';
                            data.outbound_dep_code = routes[0].querySelectorAll('.route_code__S07WE')[0]?.innerText.trim() || '';
                            data.outbound_arr_code = routes[0].querySelectorAll('.route_code__S07WE')[1]?.innerText.trim() || '';
                            data.outbound_info = routes[0].querySelector('.route_details__F_ShG')?.innerText.trim() || '';
                        }
                        if (routes[1]) {
                            data.inbound_dep_time = routes[1].querySelectorAll('.route_time__xWu7a')[0]?.innerText.trim() || '';
                            data.inbound_arr_time = routes[1].querySelectorAll('.route_time__xWu7a')[1]?.innerText.trim() || '';
                            data.inbound_dep_code = routes[1].querySelectorAll('.route_code__S07WE')[0]?.innerText.trim() || '';
                            data.inbound_arr_code = routes[1].querySelectorAll('.route_code__S07WE')[1]?.innerText.trim() || '';
                            data.inbound_info = routes[1].querySelector('.route_details__F_ShG')?.innerText.trim() || '';
                        }
                    } else if (diffAirlineBlocks.length > 0) {
                        data.airline_type = 'Different';
                        if (diffAirlineBlocks[0]) {
                            data.outbound_airline = diffAirlineBlocks[0].querySelector('.airline_name__0Tw5w')?.innerText.trim() || 'N/A';
                            const out_route = diffAirlineBlocks[0].querySelector('.route_Route__HYsDn');
                            if(out_route){
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
                             if(in_route){
                                data.inbound_dep_time = in_route.querySelectorAll('.route_time__xWu7a')[0]?.innerText.trim() || '';
                                data.inbound_arr_time = in_route.querySelectorAll('.route_time__xWu7a')[1]?.innerText.trim() || '';
                                data.inbound_dep_code = in_route.querySelectorAll('.route_code__S07WE')[0]?.innerText.trim() || '';
                                data.inbound_arr_code = in_route.querySelectorAll('.route_code__S07WE')[1]?.innerText.trim() || '';
                                data.inbound_info = in_route.querySelector('.route_details__F_ShG')?.innerText.trim() || '';
                            }
                        }
                        data.airline = `[왕복다름] ${data.outbound_airline || 'N/A'} / ${data.inbound_airline || 'N/A'}`;
                    }
                    // --- (스크래핑 로직 끝) ---

                    results.push(data);
                    console.log(`✓ [H] Item ${results.length}/${maxItems} collected: ${data.airline} - ${data.price}원`);

                } catch (e) {
                    console.error(`Error at item index ${processedIndex}:`, e.message);
                }
                processedIndex++; // (H) 다음 인덱스로 이동
            }

            // (I) 목표를 달성했으면 메인 루프 종료
            if (results.length >= maxItems) {
                break;
            }

            // (J) 스크롤 트리거: 마지막으로 처리한 항목을 뷰로 이동시킴
            const lastProcessedItem = items[items.length - 1];
            if (lastProcessedItem) {
                lastProcessedItem.scrollIntoView();
            } else {
                // 항목이 하나도 없으면 종료
                break;
            }
            
            // (K) "똑똑한 대기" 실행: 
            // 새 항목이 로드될 때까지(즉, 항목 개수가 processedIndex보다 많아질 때까지)
            // 최대 5초간 기다립니다.
            try {
                await waitForNewItem(itemSelector, processedIndex);
            } catch (e) {
                // (L) 타임아웃 발생 (더 이상 로드할 항목이 없음)
                console.warn(e.message);
                break; // 메인 루프 종료
            }
        } // (E) 메인 루프 끝
        
        console.log(`=== 총 ${results.length}개 항공권 추출 완료 ===`);
        return results; // (M) 최종 결과를 Python으로 반환
    }
    '''
    
    # (N) Python 영역: 타임아웃 설정 (방법 2와 동일)
    # (스크립트 총 실행 시간을 90초로 제한)
    page.set_default_timeout(90000) # 90초
    
    flights_data = [] # 결과물 초기화
    
    try:
        # (O) 하이브리드 스크립트 실행!
        flights_data = await page.evaluate(scroll_and_scrape_script_hybrid, max_items_to_scrape)
        
    except Exception as e:
        print(f"✗ page.evaluate() (방법 3) 실행 중 오류 발생: {e}")
        # 오류 발생 시 빈 리스트가 반환됨 (Fallback 로직에서 처리)
        
    finally:
        # (P) 타임아웃 원상 복구
        page.set_default_timeout(30000) # 30초
    
    print(f"\n✅ JavaScript (방법 3) 추출 완료: {len(flights_data)}개")
    df = pd.DataFrame(flights_data)
    return df


async def scrape_naver(
    trip_type="roundtrip",
    dep3=None,
    arr3=None,
    depdate=None,
    retdate=None,
    max_items_to_scrape=None,
    headless=False,
    output_format="csv",
    output_dir="./result",
):
    """
    네이버 항공권 사이트를 크롤링하는 함수
    [수정] 방법 2를 우선 시도하고, 실패하거나 결과가 비었을 때 방법 1로 자동 전환.
    """
    print("네이버 항공권 크롤링을 시작합니다...")
    async with async_playwright() as p: 

        #@@@ 변수 선언파트@@@@@@@@@@@@@@@@@@@@@@@@
        
        # 오늘 날짜 기준으로 기본값 설정
        today = datetime.date.today()
        default_dep_date = today + datetime.timedelta(days=1)   #내일을 출발 기본일로
        default_ret_date = today + datetime.timedelta(days=2)   #모레를 도착 기본일로

        depyyyymm = default_dep_date.strftime('%Y.%m.')
        depdd = default_dep_date.day
        retyyyymm = default_ret_date.strftime('%Y.%m.')
        retdd = default_ret_date.day
        
        dep3_default = 'ICN'    #출발 공항 3자리 코드
        arr3_default = 'TPE'    #도착 공항 3자리 코드
        depdate_default_str = default_dep_date.strftime('%Y%m%d')   #출발일 기본값 설정! 
        retdate_default_str = default_ret_date.strftime('%Y%m%d')   #도착일 기본값 설정! 

        #입력받기_________________(인수가 없을 때만 터미널에서 질문)___________________________

        ##출발 공항 입력
        if dep3 is None:
            while True:
                dep3 = input(f"출발 공항을 입력하세요(IATA 3자리 코드, 예: {dep3_default}) : ")
                if not dep3: # 엔터만 치면 기본값 사용
                    dep3 = dep3_default
                    print(f"기본값 {dep3}을 사용합니다.")
                    break

                dep3 = dep3.upper() # 소문자를 대문자로
                if dep3.isalpha() and len(dep3) == 3:
                    break
                print("✗ 잘못된 형식입니다. 반드시 알파벳 3자리로 입력해주세요.")
        else:
            dep3 = dep3.upper() # 소문자를 대문자로
            if not (dep3.isalpha() and len(dep3) == 3):
                raise ValueError("출발 공항은 IATA 알파벳 3자리 코드여야 합니다.")

        ##도착 공항 입력
        if arr3 is None:
            while True:
                arr3 = input(f"도착 공항을 입력하세요(IATA 3자리 코드, 예: {arr3_default}) : ")
                if not arr3: # 엔터만 치면 기본값 사용
                    arr3 = arr3_default
                    print(f"기본값 {arr3}을 사용합니다.")
                    break

                arr3 = arr3.upper() # 소문자를 대문자로
                if arr3.isalpha() and len(arr3) == 3:
                    break
                print("✗ 잘못된 형식입니다. 반드시 알파벳 3자리로 입력해주세요.")
        else:
            arr3 = arr3.upper() # 소문자를 대문자로
            if not (arr3.isalpha() and len(arr3) == 3):
                raise ValueError("도착 공항은 IATA 알파벳 3자리 코드여야 합니다.")


        ##출발일 입력
        if depdate is None:
            while True:
                depdate = input(f"출발 연월일을 입력하세요(YYYYMMDD, 예: {depdate_default_str}) :")
                if not depdate: #아무것도 압력하지 않으면 cuz. 파이썬에서 빈 문자열은 False이다.
                    depdate = depdate_default_str
                    print(f"기본값 {depdate}를 사용합니다.")
                    break
                if not is_valid_date(depdate):
                    print("✗ 잘못된 날짜 형식입니다. YYYYMMDD 8자리 숫자로 올바르게 입력해주세요.")
                    continue

                if today.strftime('%Y%m%d') < depdate:  #내일부터 출발 가능! 네이버 항공권 시스템 상 오늘 선택 불가.
                    break
                print("✗  출발일이 오늘보다 빠를 수 없습니다. 다시 입력해 주세요.")
        else:
            if not is_valid_date(depdate):
                raise ValueError("출발일은 YYYYMMDD 형식의 올바른 날짜여야 합니다.")
            if today.strftime('%Y%m%d') >= depdate:
                raise ValueError("출발일은 오늘 이후 날짜여야 합니다.")


        if trip_type not in ("roundtrip", "oneway"):
            raise ValueError("여정 방식은 roundtrip 또는 oneway여야 합니다.")

        #도착일 입력
        if trip_type == "oneway":
            retdate = ""
        elif retdate is None:
            while True:
                retdate = input(f"복귀 연월일을 입력하세요(YYYYMMDD, 예: {retdate_default_str}) :")
                if not retdate:
                    retdate = retdate_default_str
                    print(f"기본값 {retdate}를 사용합니다.")

                if not is_valid_date(retdate):
                    print("✗ 잘못된 날짜 형식입니다. YYYYMMDD 8자리 숫자로 올바르게 입력해주세요.")
                    continue

                if depdate < retdate:
                    break
                print("✗ 다시 입력 해주세요. 복귀일이 출발일보다 빠르거나 같을 수 없습니다.")
        else:
            if not is_valid_date(retdate):
                raise ValueError("복귀일은 YYYYMMDD 형식의 올바른 날짜여야 합니다.")
            if depdate >= retdate:
                raise ValueError("복귀일은 출발일보다 늦어야 합니다.")

        # 크롤링할 데이터 개수 입력
        max_items_to_scrape_default = 30
        if max_items_to_scrape is None:
            while True:
                max_items_input = input(f"스크래핑할 최대 항목 수를 입력하세요 (기본값: {max_items_to_scrape_default}) : ")
                if not max_items_input:
                    max_items_to_scrape = max_items_to_scrape_default
                    print(f"기본값 {max_items_to_scrape}개를 사용합니다.")
                    break

                if max_items_input.isdigit() and int(max_items_input) > 0:
                    max_items_to_scrape = int(max_items_input)
                    break
                print("✗ 잘못된 형식입니다. 0보다 큰 숫자로 입력해주세요.")
        elif max_items_to_scrape <= 0:
            raise ValueError("수집 개수는 1 이상이어야 합니다.")
        # -----------------------------------------

        # 입력값을 날짜 형식 변수로 변환
        depyyyymm = depdate[:4]+'.'+depdate[4:6]+'.'
        depdd = int(depdate[6:])
        retyyyymm = retdate[:4]+'.'+retdate[4:6]+'.' if retdate else ""
        retdd = int(retdate[6:]) if retdate else 0
        
        #___________입력 끝_____________________________________________________________________________

        profile = generate_random_profile()
        profile['locale'] = 'ko-KR'
        profile['timezone_id'] = 'Asia/Seoul'
        print_profile_info(profile)
        
        browser = await p.firefox.launch(headless=headless)
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
        await close_ad_popup_if_present(page)
        #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        await select_naver_trip_type(page, trip_type)

        #______출발지 설정_______________________________________________________________________________________
        ##출발지 공항 이름 입력하기
        await page.locator('button.tabContent_route__EXyDz.select_City__mKbzk.select_start__zx2PH').click() ##요소 찾기 (로케이터)
        # HTML에서 그대로 붙여넣기 하면 안되고 -> 태그.클래스값(단 붙여넣기 한 것 안의 띄어쓰기를 .으로 대체해야 함!)
        # 띄어쓰기를 없애고 클래스 이름 앞에 모두 .을 붙입니다.
        await asyncio.sleep(generate_random_short_delay())
        if not await insert_airport(page, dep3, "출발지"):
            raise RuntimeError(f"{dep3} 출발지 선택에 실패했습니다.")
        
        #______도착지 설정_______________________________________________________________________________________
        ##도착지 공항 이름 입력하기
        await page.locator('button.tabContent_route__EXyDz.select_City__mKbzk.select_end__pdCjg').click() ##요소 찾기 (로케이터)
        # HTML에서 그대로 붙여넣기 하면 안되고 -> 태그.클래스값(단 붙여넣기 한 것 안의 띄어쓰기를 .으로 대체해야 함!)
        # 띄어쓰기를 없애고 클래스 이름 앞에 모두 .을 붙입니다.
        await asyncio.sleep(generate_random_short_delay())
        if not await insert_airport(page, arr3, "도착지"):
            raise RuntimeError(f"{arr3} 도착지 선택에 실패했습니다.")


        #____playwright에서 마우스로 선택_________________________________________________________________
        #가는날 선택      
        await page.get_by_role('button', name='가는 날').click()
        await page.mouse.wheel(0, 700)      #휠 아래로 조금 내리기
        await asyncio.sleep(generate_random_short_delay())

        if not await click_calendar_date(page, depyyyymm, depdd, start_from_visible=False): #날짜 선택하는 함수!
            raise RuntimeError(f"{depdate} 출발일 선택에 실패했습니다.")
        await asyncio.sleep(generate_random_short_delay())

        #오는날 선택
        if trip_type == "roundtrip":
            if not await click_calendar_date(page, retyyyymm, retdd, start_from_visible=True): #날짜 선택하는 함수!
                raise RuntimeError(f"{retdate} 복귀일 선택에 실패했습니다.")

        #검색버튼 누르기
        # --- 수정: '검색' 이름의 버튼이 2개 발견되는 오류(strict mode violation) 해결 ---
        await page.get_by_role('button', name='검색', exact=True).click()

        # --- 중요: 여기가 수정된 부분 ---
        # (새로운 수정) 대기 없이는 스크롤이 안되므로, '스피너'가 나타났다가
        # 사라지는 것만 대기하여 로딩을 보장합니다. (가장 빠르고 안정적인 방법)
        print("\n[Wait] 항공권 검색 시작... (스피너 대기 중)")
        await wait_for_flight_results(page)
        
        # -------------------------------


        # --- (★ 여기가 수정된 핵심 로직입니다 ★) ---
        
        saved_info = pd.DataFrame() # 최종 결과를 담을 DataFrame 초기화

        #3번 방법으로 실행.
        saved_info = await scrape_flights_hybrid(page, max_items_to_scrape=max_items_to_scrape)
        if not saved_info.empty:
            saved_info["trip_type"] = trip_type
            if trip_type == "oneway":
                for column in [
                    "inbound_dep_time",
                    "inbound_arr_time",
                    "inbound_dep_code",
                    "inbound_arr_code",
                    "inbound_info",
                ]:
                    saved_info[column] = ""

        # --- (수정) 최종 결과 확인 및 저장 ---
        if saved_info.empty:
            print("\n❌ 최종 스크래핑 실패: 수집된 데이터가 없습니다. 엑셀 파일을 저장하지 않습니다.")
        else:
            print("\n--- 최종 결과 (상위 5개) ---")
            print(saved_info.head())
            print("--------------------------\n")

            # --- 결과 저장 ---
            save_directory = output_dir        #상위 디렉토리에 result에 저장
            os.makedirs(save_directory, exist_ok=True)

            if output_format == "xlsx":
                output_path = f'{save_directory}/{dep3}_TO_{arr3}_{output_date_suffix(depdate, retdate, trip_type)}.xlsx'
                saved_info.to_excel(output_path, index=False)
                print(f"✓ 검색결과가 Excel 파일로 저장되었습니다. ({output_path})")
            else:
                output_path = f'{save_directory}/{dep3}_TO_{arr3}_{output_date_suffix(depdate, retdate, trip_type)}.csv'
                saved_info.to_csv(output_path, index=False, encoding='utf-8-sig')
                print(f"✓ 검색결과가 CSV 파일로 저장되었습니다. ({output_path})")

            #excel_filename = f'./result/SEL_TO_{arr3}_{depdate}-{retdate}.xlsx'
            #saved_info.to_excel(excel_filename, index=False)
            #print(f"✓ 검색결과가 Excel 파일로 저장되었습니다. ({excel_filename})")
        
        # --- (여기까지가 수정된 로직입니다) ---


        print("\n\n이용해주셔서 감사합니다 :)")
        await asyncio.sleep(1)
        
        # browser를 닫습니다.
        await browser.close() 
        
        print("***크롤링을 종료합니다***")
        return saved_info
