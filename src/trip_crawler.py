import asyncio
import datetime
import os
import re
from urllib.parse import urlencode

import pandas as pd
from playwright.async_api import TimeoutError, async_playwright

from utils import generate_random_profile, is_valid_date, print_profile_info


TRIP_FLIGHTS_URL = "https://www.trip.com/flights/?locale=en-XX&curr=KRW"
TRIP_FLIGHT_ITEM_SELECTOR = ".f-info-content"

MONTH_NAMES = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]
WEEKDAY_NAMES = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]


def output_date_suffix(depdate, retdate, trip_type):
    return f"{depdate}-oneway" if trip_type == "oneway" else f"{depdate}-{retdate}"


def yyyymmdd_to_iso(value):
    return f"{value[:4]}-{value[4:6]}-{value[6:]}"


def build_trip_search_url(dep3, arr3, depdate, retdate, trip_type):
    params = {
        "dcity": dep3.lower(),
        "acity": arr3.lower(),
        "ddate": yyyymmdd_to_iso(depdate),
        "dairport": dep3.lower(),
        "aairport": arr3.lower(),
        "triptype": "ow" if trip_type == "oneway" else "rt",
        "class": "y",
        "quantity": "1",
        "searchboxarg": "t",
        "nonstoponly": "off",
        "locale": "en-XX",
        "curr": "KRW",
    }
    if trip_type == "roundtrip":
        params["rdate"] = yyyymmdd_to_iso(retdate)
    return f"https://www.trip.com/flights/showfarefirst?{urlencode(params)}"


def normalize_airport(value, field_name):
    airport = (value or "").upper()
    if not (airport.isalpha() and len(airport) == 3):
        raise ValueError(f"{field_name} 공항은 IATA 알파벳 3자리 코드여야 합니다.")
    return airport


def validate_common_args(dep3, arr3, depdate, retdate, max_items_to_scrape, trip_type):
    today = datetime.date.today().strftime("%Y%m%d")

    dep3 = normalize_airport(dep3, "출발")
    arr3 = normalize_airport(arr3, "도착")
    if trip_type not in ("roundtrip", "oneway"):
        raise ValueError("여정 방식은 roundtrip 또는 oneway여야 합니다.")
    if not is_valid_date(depdate):
        raise ValueError("출발일은 YYYYMMDD 형식의 올바른 날짜여야 합니다.")
    if trip_type == "roundtrip" and not is_valid_date(retdate):
        raise ValueError("복귀일은 YYYYMMDD 형식의 올바른 날짜여야 합니다.")
    if depdate < today:
        raise ValueError("출발일은 오늘보다 빠를 수 없습니다.")
    if trip_type == "roundtrip" and depdate >= retdate:
        raise ValueError("복귀일은 출발일보다 늦어야 합니다.")
    if max_items_to_scrape <= 0:
        raise ValueError("수집 개수는 1 이상이어야 합니다.")

    return dep3, arr3


def yyyymmdd_to_date(value):
    return datetime.datetime.strptime(value, "%Y%m%d").date()


def trip_date_label(value):
    date = yyyymmdd_to_date(value)
    return f"{WEEKDAY_NAMES[date.weekday()]}, {MONTH_NAMES[date.month - 1]} {date.day}, {date.year}"


async def click_if_visible(locator, timeout=1500):
    try:
        if await locator.count() > 0 and await locator.first.is_visible():
            await locator.first.click(timeout=timeout)
            return True
    except Exception:
        return False
    return False


async def close_trip_prompts(page):
    await click_if_visible(page.locator('[data-testid="online_index_click_chromePluginV2_close"]'), timeout=1000)
    await click_if_visible(page.locator('[aria-label="Close"]').first, timeout=1000)


async def select_trip_airport(page, airport3, input_test_id, field_label):
    print(f"... Trip.com {field_label} 공항을 {airport3}(으)로 설정 중")
    await close_trip_prompts(page)

    inputs = page.locator(f'input[data-testid="{input_test_id}"]')
    await inputs.last.wait_for(state="attached", timeout=15000)
    await inputs.last.click()
    await inputs.last.fill(airport3)

    result_box = page.locator('[data-testid="search_result_box"]').last
    await result_box.wait_for(state="visible", timeout=12000)
    option = result_box.get_by_text(re.compile(rf"^{re.escape(airport3)}\b")).first
    await option.wait_for(state="visible", timeout=12000)
    await option.click()
    await page.wait_for_timeout(700)
    print(f"✓ {field_label} 공항 설정 완료: {airport3}")


async def select_trip_type(page, trip_type):
    if trip_type != "oneway":
        return

    print("... Trip.com 여정 방식을 편도로 설정 중")
    await close_trip_prompts(page)
    candidates = [
        page.locator('[data-testid="flightType_OW"]'),
        page.locator('[role="radio"][aria-label="One-way"]'),
        page.get_by_text("One-way", exact=True),
        page.get_by_text("One Way", exact=True),
    ]
    for candidate in candidates:
        try:
            if await candidate.count() > 0:
                await candidate.first.click(timeout=3000)
                await page.wait_for_timeout(700)
                print("✓ Trip.com 편도 설정 완료")
                return
        except Exception:
            pass

    raise RuntimeError("Trip.com 편도 버튼을 찾지 못했습니다.")


async def click_trip_date(page, date_value):
    label = trip_date_label(date_value)
    selector = f'div[aria-label^="{label}"]'

    for _ in range(14):
        date_cell = page.locator(selector).first
        if await date_cell.count() > 0:
            await date_cell.scroll_into_view_if_needed()
            await date_cell.click()
            print(f"✓ 날짜 선택 완료: {date_value}")
            await page.wait_for_timeout(500)
            return

        next_month = page.locator('[aria-label="Go to next month"]').first
        if await next_month.count() == 0:
            break
        await next_month.click()
        await page.wait_for_timeout(400)

    raise TimeoutError(f"Trip.com 날짜를 찾지 못했습니다: {label}")


async def select_trip_dates(page, depdate, retdate, trip_type):
    date_text = depdate if trip_type == "oneway" else f"{depdate} ~ {retdate}"
    print(f"... Trip.com 날짜 선택 중: {date_text}")
    date_input = page.locator('input[data-testid="search_date_depart0"]').first
    await date_input.wait_for(state="visible", timeout=10000)
    await date_input.click()
    await page.locator('[data-testid="range_calendar"]').wait_for(state="visible", timeout=10000)

    await click_trip_date(page, depdate)
    if trip_type == "roundtrip":
        await click_trip_date(page, retdate)


async def wait_for_trip_results(page):
    print("\n[Wait] Trip.com 검색 결과 로딩 중...")
    await page.wait_for_load_state("domcontentloaded")
    await page.locator(TRIP_FLIGHT_ITEM_SELECTOR).first.wait_for(state="visible", timeout=60000)
    await page.wait_for_timeout(2500)
    print("✓ Trip.com 검색 결과가 표시되었습니다.")


def parse_trip_price(value):
    krw_match = re.search(r"(?:KRW|₩)\s?([\d,]+)", value)
    if krw_match:
        return int(krw_match.group(1).replace(",", ""))

    usd_match = re.search(r"US\$\s?([\d,]+)", value)
    return f"US${usd_match.group(1)}" if usd_match else ""


def parse_trip_card(raw_text, dep3, arr3, retdate, trip_type):
    lines = [
        line.replace("\u00a0", " ").strip()
        for line in raw_text.splitlines()
        if line.replace("\u00a0", " ").strip()
    ]
    if not lines:
        return None

    price_line = next((line for line in lines if re.search(r"(?:KRW|₩|US\$)", line)), "")
    price = parse_trip_price(price_line)
    if not price:
        return None

    skip_labels = {
        "Included",
        "Cheapest",
        "Recommended",
        "Student Tickets Available",
        "Round-trip",
        "Select",
    }
    time_pattern = re.compile(r"^\d{1,2}:\d{2}$")
    dep_time_index = next((idx for idx, line in enumerate(lines) if time_pattern.match(line)), -1)
    if dep_time_index <= 0:
        return None

    airline_parts = [
        line
        for line in lines[:dep_time_index]
        if line not in skip_labels and not line.startswith("- ") and "CO2e" not in line
    ]
    airline = " ".join(airline_parts) or "N/A"

    dep_time = lines[dep_time_index]
    dep_code_line = lines[dep_time_index + 1] if dep_time_index + 1 < len(lines) else ""
    duration = lines[dep_time_index + 2] if dep_time_index + 2 < len(lines) else ""
    stop_info = lines[dep_time_index + 3] if dep_time_index + 3 < len(lines) else ""
    arr_time = lines[dep_time_index + 4] if dep_time_index + 4 < len(lines) else ""
    arr_code_line = lines[dep_time_index + 5] if dep_time_index + 5 < len(lines) else ""

    dep_code_match = re.search(r"\b([A-Z]{3})", dep_code_line)
    arr_code_match = re.search(r"\b([A-Z]{3})", arr_code_line)
    dep_code = dep_code_match.group(1) if dep_code_match else dep3
    arr_code = arr_code_match.group(1) if arr_code_match else arr3
    outbound_info = " / ".join(
        part for part in [duration, stop_info] if part and not re.search(r"(?:KRW|₩|US\$)", part)
    )

    return {
        "price": price,
        "airline_type": "Trip.com",
        "airline": airline,
        "outbound_dep_time": dep_time,
        "outbound_arr_time": arr_time,
        "outbound_dep_code": dep_code,
        "outbound_arr_code": arr_code,
        "outbound_info": outbound_info,
        "inbound_dep_time": "",
        "inbound_arr_time": "",
        "inbound_dep_code": arr3 if trip_type == "roundtrip" else "",
        "inbound_arr_code": dep3 if trip_type == "roundtrip" else "",
        "inbound_info": (
            f"Trip.com 왕복가 기준, 복귀일 {retdate}, 표시 통화 KRW"
            if trip_type == "roundtrip"
            else "Trip.com 편도 기준, 표시 통화 KRW"
        ),
        "source": "trip",
        "trip_type": trip_type,
    }


async def scrape_trip_flights(page, dep3, arr3, retdate, max_items_to_scrape, trip_type):
    print(f"\n[Scraping] Trip.com 결과 수집 중 (목표: {max_items_to_scrape}개)")
    rows = await page.evaluate(
        """
        (selector) => Array.from(document.querySelectorAll(selector))
            .map((item) => {
                const bookingLink = item.querySelector("a[href]") || item.closest("a[href]");
                return {
                    text: item.innerText || item.textContent || "",
                    booking_url: bookingLink
                        ? new URL(bookingLink.getAttribute("href"), window.location.href).href
                        : window.location.href,
                };
            })
            .filter((row) => row.text)
        """,
        TRIP_FLIGHT_ITEM_SELECTOR,
    )

    flights = []
    seen = set()
    for row in rows:
        raw_text = row.get("text", "") if isinstance(row, dict) else str(row)
        booking_url = row.get("booking_url", "") if isinstance(row, dict) else ""
        parsed = parse_trip_card(raw_text, dep3, arr3, retdate, trip_type)
        if not parsed:
            continue
        parsed["booking_url"] = booking_url

        key = (
            parsed["airline"],
            parsed["outbound_dep_time"],
            parsed["outbound_arr_time"],
            parsed["price"],
        )
        if key in seen:
            continue
        seen.add(key)
        flights.append(parsed)

        if len(flights) >= max_items_to_scrape:
            break

    print(f"✅ Trip.com 추출 완료: {len(flights)}개")
    return pd.DataFrame(flights)


async def scrape_trip(
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
    print("Trip.com 크롤링을 시작합니다...")

    today = datetime.date.today()
    dep3 = dep3 or "ICN"
    arr3 = arr3 or "TPE"
    depdate = depdate or (today + datetime.timedelta(days=1)).strftime("%Y%m%d")
    retdate = retdate or ((today + datetime.timedelta(days=2)).strftime("%Y%m%d") if trip_type == "roundtrip" else "")
    max_items_to_scrape = max_items_to_scrape or 30
    dep3, arr3 = validate_common_args(dep3, arr3, depdate, retdate, max_items_to_scrape, trip_type)

    profile = generate_random_profile()
    profile["locale"] = "en-US"
    profile["timezone_id"] = "Asia/Seoul"
    print_profile_info(profile)

    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=headless)
        context = await browser.new_context(
            user_agent=profile["user_agent"],
            locale=profile["locale"],
            timezone_id=profile["timezone_id"],
            viewport=profile["viewport"],
        )
        page = await context.new_page()

        try:
            start_url = build_trip_search_url(dep3, arr3, depdate, retdate, trip_type) if trip_type == "oneway" else TRIP_FLIGHTS_URL
            await page.goto(start_url, wait_until="domcontentloaded")
            print("Trip.com 항공권 페이지에 접속했습니다.")
            print(f"페이지 제목: {await page.title()}")

            if trip_type == "roundtrip":
                await select_trip_airport(page, dep3, "search_city_from0", "출발")
                await select_trip_airport(page, arr3, "search_city_to0", "도착")
                await select_trip_dates(page, depdate, retdate, trip_type)
                await page.locator('[data-testid="search_btn"]').first.click()
            else:
                print("✓ Trip.com 편도 검색 URL로 직접 이동했습니다.")

            await wait_for_trip_results(page)

            saved_info = await scrape_trip_flights(page, dep3, arr3, retdate, max_items_to_scrape, trip_type)
            if saved_info.empty:
                print("\n❌ 최종 스크래핑 실패: 수집된 데이터가 없습니다.")
                return saved_info

            print("\n--- 최종 결과 (상위 5개) ---")
            print(saved_info.head())
            print("--------------------------\n")

            os.makedirs(output_dir, exist_ok=True)
            if output_format == "xlsx":
                output_path = f"{output_dir}/trip_{dep3}_TO_{arr3}_{output_date_suffix(depdate, retdate, trip_type)}.xlsx"
                saved_info.to_excel(output_path, index=False)
                print(f"✓ 검색결과가 Excel 파일로 저장되었습니다. ({output_path})")
            else:
                output_path = f"{output_dir}/trip_{dep3}_TO_{arr3}_{output_date_suffix(depdate, retdate, trip_type)}.csv"
                saved_info.to_csv(output_path, index=False, encoding="utf-8-sig")
                print(f"✓ 검색결과가 CSV 파일로 저장되었습니다. ({output_path})")

            return saved_info
        except TimeoutError as error:
            await page.screenshot(path="./error_trip_timeout.png")
            print("오류 발생 시점의 스크린샷을 'error_trip_timeout.png'로 저장했습니다.")
            raise error
        finally:
            await asyncio.sleep(1)
            await browser.close()
            print("***Trip.com 크롤링을 종료합니다***")
