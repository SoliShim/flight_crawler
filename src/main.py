import asyncio
from naver_crawler import scrape_naver
from cau_crawler import scrape_cau
from google_crawler import scrape_google_flight

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