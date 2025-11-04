import random
import datetime

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
def generate_random_short_delay(min_val=0.2, max_val=0.7, decimal_places=4):
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
        datetime.datetime.strptime(date_string, '%Y%m%d')   #월이 맞는지 확인
        return True
    except ValueError:
        return False