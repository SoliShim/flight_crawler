import asyncio
import datetime
import os
import re

import pandas as pd
from playwright.async_api import TimeoutError, async_playwright

from utils import generate_random_profile, is_valid_date, print_profile_info


GOOGLE_FLIGHTS_URL = "https://www.google.com/travel/flights?hl=ko&gl=KR&curr=KRW"
FLIGHT_ITEM_SELECTOR = "li.pIav2d"


def output_date_suffix(depdate, retdate, trip_type):
    return f"{depdate}-oneway" if trip_type == "oneway" else f"{depdate}-{retdate}"


def yyyymmdd_to_iso(value):
    return f"{value[:4]}-{value[4:6]}-{value[6:]}"


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


async def click_if_visible(locator, timeout=1500):
    try:
        if await locator.count() > 0 and await locator.first.is_visible():
            await locator.first.click(timeout=timeout)
            return True
    except Exception:
        return False
    return False


async def select_google_airport(page, airport3, field_label):
    print(f"... Google Flights {field_label} 공항을 {airport3}(으)로 설정 중")
    trigger = page.get_by_label(field_label, exact=False).first
    await trigger.wait_for(state="visible", timeout=15000)
    await trigger.click()

    dialog_input = page.locator('div[role="dialog"] input[role="combobox"]:visible').last
    await dialog_input.wait_for(state="visible", timeout=10000)
    await dialog_input.fill(airport3)

    option = page.locator('li[role="option"]', has_text=airport3).first
    await option.wait_for(state="visible", timeout=10000)
    await option.click()
    await page.wait_for_timeout(700)
    print(f"✓ {field_label} 공항 설정 완료: {airport3}")


async def select_google_trip_type(page, trip_type):
    if trip_type != "oneway":
        return

    print("... Google Flights 여정 방식을 편도로 설정 중")
    trigger_clicked = await page.evaluate(
        """
        () => {
            const isVisible = (element) => {
                const rect = element.getBoundingClientRect();
                const style = window.getComputedStyle(element);
                return rect.width > 0 && rect.height > 0 && style.visibility !== "hidden" && style.display !== "none";
            };
            const exactText = (element) => (element.innerText || element.textContent || "").trim();
            const trigger = Array.from(document.querySelectorAll('[role="combobox"], button, div'))
                .find((element) => exactText(element) === "왕복" && isVisible(element));
            if (!trigger) return false;
            trigger.click();
            return true;
        }
        """
    )
    if trigger_clicked:
        await page.wait_for_timeout(500)

    clicked = await page.evaluate(
        """
        () => {
            const isVisible = (element) => {
                const rect = element.getBoundingClientRect();
                const style = window.getComputedStyle(element);
                return rect.width > 0 && rect.height > 0 && style.visibility !== "hidden" && style.display !== "none";
            };
            const exactText = (element) => (element.innerText || element.textContent || "").trim();
            const options = Array.from(document.querySelectorAll('[role="option"], [role="listbox"] *, li, span, div'))
                .filter((element) => exactText(element) === "편도");
            const option = options.find((element) => element.closest('[role="listbox"]') && isVisible(element))
                || options.find((element) => element.closest('[role="listbox"]'))
                || options.find(isVisible)
                || options[0];
            if (!option) return false;
            option.click();
            return true;
        }
        """
    )
    if clicked:
        await page.wait_for_timeout(700)
        print("✓ Google Flights 편도 설정 완료")
        return

    triggers = [
        page.get_by_role("combobox").filter(has_text=re.compile("왕복|편도")).first,
        page.get_by_text("왕복", exact=True).first,
    ]
    for trigger in triggers:
        try:
            if await trigger.count() > 0 and await trigger.is_visible():
                await trigger.click(timeout=3000)
                option = page.get_by_text("편도", exact=True).last
                await option.wait_for(state="visible", timeout=5000)
                await option.click(timeout=3000)
                await page.wait_for_timeout(700)
                print("✓ Google Flights 편도 설정 완료")
                return
        except Exception:
            pass

    raise RuntimeError("Google Flights 편도 선택 메뉴를 찾지 못했습니다.")


async def select_google_dates(page, depdate, retdate, trip_type):
    date_text = depdate if trip_type == "oneway" else f"{depdate} ~ {retdate}"
    print(f"... Google Flights 날짜 선택 중: {date_text}")
    await page.get_by_label("출발", exact=True).first.click()

    dep_iso = yyyymmdd_to_iso(depdate)
    date_targets = [(dep_iso, "출발일")]
    if trip_type == "roundtrip":
        date_targets.append((yyyymmdd_to_iso(retdate), "복귀일"))

    for iso_date, label in date_targets:
        date_cell = page.locator(f'[data-iso="{iso_date}"]').first
        await date_cell.wait_for(state="attached", timeout=10000)
        await date_cell.scroll_into_view_if_needed()
        await date_cell.click()
        print(f"✓ {label} 선택 완료: {iso_date}")
        await page.wait_for_timeout(500)

    await page.locator('button:has-text("확인"):visible').last.click()
    await page.wait_for_timeout(700)


async def wait_for_google_results(page):
    print("\n[Wait] Google Flights 검색 결과 로딩 중...")
    await page.locator('main, [role="main"]').first.wait_for(state="visible", timeout=30000)
    await page.locator(FLIGHT_ITEM_SELECTOR).first.wait_for(state="visible", timeout=45000)
    await page.wait_for_timeout(2500)
    print("✓ Google Flights 검색 결과가 표시되었습니다.")


async def expand_google_results(page, target_count):
    for _ in range(5):
        count = await page.locator(FLIGHT_ITEM_SELECTOR).count()
        if count >= target_count:
            return

        expanded = await click_if_visible(page.get_by_text("항공편 더보기", exact=True), timeout=3000)
        if not expanded:
            return
        await page.wait_for_timeout(1500)


def parse_google_time(value):
    return value.replace("\u00a0", " ").strip()


def parse_google_price(value):
    match = re.search(r"₩\s?([\d,]+)", value)
    if not match:
        return None
    return int(match.group(1).replace(",", ""))


async def scrape_google_flights(page, dep3, arr3, retdate, max_items_to_scrape, trip_type):
    print(f"\n[Scraping] Google Flights 결과 수집 중 (목표: {max_items_to_scrape}개)")
    rows = await page.evaluate(
        """
        (selector) => Array.from(document.querySelectorAll(selector))
            .map((item) => {
                const parts = [item.innerText, item.textContent];
                item.querySelectorAll("[aria-label]").forEach((node) => {
                    parts.push(node.getAttribute("aria-label"));
                });
                const bookingLink = item.querySelector("a[href]") || item.closest("a[href]");
                return {
                    text: parts.filter(Boolean).join("\\n"),
                    booking_url: bookingLink
                        ? new URL(bookingLink.getAttribute("href"), window.location.href).href
                        : window.location.href,
                };
            })
            .filter((row) => row.text)
        """,
        FLIGHT_ITEM_SELECTOR,
    )

    flights = []
    route_pattern = re.compile(r"\b([A-Z]{3})[–-]([A-Z]{3})\b")
    time_pattern = re.compile(r"(?:(?:오전|오후)\s*)?\d{1,2}:\d{2}(?:\+\d+)?")

    for row in rows:
        raw_text = row.get("text", "") if isinstance(row, dict) else str(row)
        booking_url = row.get("booking_url", "") if isinstance(row, dict) else ""
        lines = [
            line.replace("\u00a0", " ").strip()
            for line in raw_text.splitlines()
            if line.replace("\u00a0", " ").strip()
        ]
        if not lines:
            continue

        price_line = next((line for line in lines if "₩" in line), "")
        price = parse_google_price(price_line)
        route_index = next((idx for idx, line in enumerate(lines) if route_pattern.search(line)), -1)
        if price is None or route_index < 0:
            continue

        route_match = route_pattern.search(lines[route_index])
        dep_code = route_match.group(1)
        arr_code = route_match.group(2)
        time_text = " ".join(lines[:route_index])
        times = [parse_google_time(match) for match in time_pattern.findall(time_text)]
        dep_time = times[0] if len(times) > 0 else ""
        arr_time = times[1] if len(times) > 1 else ""
        airline = lines[route_index - 2] if route_index >= 2 else "N/A"
        duration = lines[route_index - 1] if route_index >= 1 else ""
        stop_info = lines[route_index + 1] if route_index + 1 < len(lines) else ""
        layover_info = lines[route_index + 2] if route_index + 2 < len(lines) and "CO2" not in lines[route_index + 2] else ""
        outbound_info = " / ".join(part for part in [duration, stop_info, layover_info] if part)

        flights.append(
            {
                "price": price,
                "airline_type": "Google",
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
                    f"Google Flights 왕복가 기준, 복귀일 {retdate}"
                    if trip_type == "roundtrip"
                    else "Google Flights 편도 기준"
                ),
                "source": "google",
                "trip_type": trip_type,
                "booking_url": booking_url,
            }
        )

        if len(flights) >= max_items_to_scrape:
            break

    print(f"✅ Google Flights 추출 완료: {len(flights)}개")
    return pd.DataFrame(flights)


async def scrape_google(
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
    print("Google Flights 크롤링을 시작합니다...")

    today = datetime.date.today()
    dep3 = dep3 or "ICN"
    arr3 = arr3 or "TPE"
    depdate = depdate or (today + datetime.timedelta(days=1)).strftime("%Y%m%d")
    retdate = retdate or ((today + datetime.timedelta(days=2)).strftime("%Y%m%d") if trip_type == "roundtrip" else "")
    max_items_to_scrape = max_items_to_scrape or 30
    dep3, arr3 = validate_common_args(dep3, arr3, depdate, retdate, max_items_to_scrape, trip_type)

    profile = generate_random_profile()
    profile["user_agent"] = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:122.0) "
        "Gecko/20100101 Firefox/122.0"
    )
    profile["locale"] = "ko-KR"
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
            await page.goto(GOOGLE_FLIGHTS_URL, wait_until="domcontentloaded")
            print("Google Flights 페이지에 접속했습니다.")
            print(f"페이지 제목: {await page.title()}")

            await select_google_trip_type(page, trip_type)
            await select_google_airport(page, dep3, "출발지가 어디인가요?")
            await select_google_airport(page, arr3, "목적지가 어디인가요?")
            await select_google_dates(page, depdate, retdate, trip_type)

            await page.get_by_role("button", name="검색", exact=True).click()
            await wait_for_google_results(page)
            await expand_google_results(page, max_items_to_scrape)

            saved_info = await scrape_google_flights(page, dep3, arr3, retdate, max_items_to_scrape, trip_type)
            if saved_info.empty:
                print("\n❌ 최종 스크래핑 실패: 수집된 데이터가 없습니다.")
                return saved_info

            print("\n--- 최종 결과 (상위 5개) ---")
            print(saved_info.head())
            print("--------------------------\n")

            os.makedirs(output_dir, exist_ok=True)
            if output_format == "xlsx":
                output_path = f"{output_dir}/google_{dep3}_TO_{arr3}_{output_date_suffix(depdate, retdate, trip_type)}.xlsx"
                saved_info.to_excel(output_path, index=False)
                print(f"✓ 검색결과가 Excel 파일로 저장되었습니다. ({output_path})")
            else:
                output_path = f"{output_dir}/google_{dep3}_TO_{arr3}_{output_date_suffix(depdate, retdate, trip_type)}.csv"
                saved_info.to_csv(output_path, index=False, encoding="utf-8-sig")
                print(f"✓ 검색결과가 CSV 파일로 저장되었습니다. ({output_path})")

            return saved_info
        except TimeoutError as error:
            await page.screenshot(path="./error_google_timeout.png")
            print("오류 발생 시점의 스크린샷을 'error_google_timeout.png'로 저장했습니다.")
            raise error
        finally:
            await asyncio.sleep(1)
            await browser.close()
            print("***Google Flights 크롤링을 종료합니다***")
