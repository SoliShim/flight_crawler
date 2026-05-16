import argparse
import asyncio
import datetime

from utils import is_valid_date


def build_parser():
    today = datetime.date.today()
    default_dep_date = (today + datetime.timedelta(days=1)).strftime("%Y%m%d")
    default_ret_date = (today + datetime.timedelta(days=2)).strftime("%Y%m%d")

    parser = argparse.ArgumentParser(
        description="항공권 사이트를 브라우저로 직접 방문해 왕복 또는 편도 항공권 가격을 수집합니다."
    )
    parser.add_argument(
        "--source",
        choices=["naver", "google", "trip"],
        default="naver",
        help="검색 플랫폼",
    )
    parser.add_argument("--from", dest="dep3", default="ICN", help="출발 공항 IATA 코드")
    parser.add_argument("--to", dest="arr3", default="TPE", help="도착 공항 IATA 코드")
    parser.add_argument("--trip-type", choices=["roundtrip", "oneway"], default="roundtrip", help="여정 방식")
    parser.add_argument("--depart", default=default_dep_date, help="출발일 YYYYMMDD")
    parser.add_argument("--return-date", default=default_ret_date, help="복귀일 YYYYMMDD. 편도에서는 사용하지 않습니다.")
    parser.add_argument("--items", type=int, default=30, help="수집할 최대 항공권 개수")
    parser.add_argument("--format", choices=["csv", "xlsx"], default="csv", help="저장 형식")
    parser.add_argument("--output-dir", default="./result", help="결과 저장 폴더")
    parser.add_argument(
        "--headless",
        action="store_true",
        help="브라우저 창을 보이지 않고 실행합니다. 처음 확인할 때는 생략하는 것을 권장합니다.",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="터미널 질문 방식으로 실행합니다. 이 옵션을 쓰면 위 조건 옵션들은 기본값 질문으로 처리됩니다.",
    )
    return parser


def validate_args(args):
    if not args.interactive:
        if not (args.dep3.isalpha() and len(args.dep3) == 3):
            raise ValueError("--from 값은 IATA 알파벳 3자리 코드여야 합니다.")
        if not (args.arr3.isalpha() and len(args.arr3) == 3):
            raise ValueError("--to 값은 IATA 알파벳 3자리 코드여야 합니다.")
        if not is_valid_date(args.depart):
            raise ValueError("--depart 값은 YYYYMMDD 형식의 올바른 날짜여야 합니다.")
        if args.trip_type == "roundtrip":
            if not is_valid_date(args.return_date):
                raise ValueError("--return-date 값은 YYYYMMDD 형식의 올바른 날짜여야 합니다.")
            if args.depart >= args.return_date:
                raise ValueError("--return-date 값은 --depart 값보다 늦어야 합니다.")
        if args.items <= 0:
            raise ValueError("--items 값은 1 이상이어야 합니다.")


async def main():
    parser = build_parser()
    args = parser.parse_args()
    validate_args(args)

    if args.interactive:
        if args.source == "google":
            from google_crawler import scrape_google

            await scrape_google(headless=args.headless, output_format=args.format, output_dir=args.output_dir)
            return
        if args.source == "trip":
            from trip_crawler import scrape_trip

            await scrape_trip(headless=args.headless, output_format=args.format, output_dir=args.output_dir)
            return

        from naver_crawler import scrape_naver

        await scrape_naver(headless=args.headless, output_format=args.format, output_dir=args.output_dir)
        return

    if args.source == "google":
        from google_crawler import scrape_google

        await scrape_google(
            trip_type=args.trip_type,
            dep3=args.dep3,
            arr3=args.arr3,
            depdate=args.depart,
            retdate=args.return_date,
            max_items_to_scrape=args.items,
            headless=args.headless,
            output_format=args.format,
            output_dir=args.output_dir,
        )
    elif args.source == "trip":
        from trip_crawler import scrape_trip

        await scrape_trip(
            trip_type=args.trip_type,
            dep3=args.dep3,
            arr3=args.arr3,
            depdate=args.depart,
            retdate=args.return_date,
            max_items_to_scrape=args.items,
            headless=args.headless,
            output_format=args.format,
            output_dir=args.output_dir,
        )
    else:
        from naver_crawler import scrape_naver

        await scrape_naver(
            trip_type=args.trip_type,
            dep3=args.dep3,
            arr3=args.arr3,
            depdate=args.depart,
            retdate=args.return_date,
            max_items_to_scrape=args.items,
            headless=args.headless,
            output_format=args.format,
            output_dir=args.output_dir,
        )


if __name__ == "__main__":
    asyncio.run(main())
