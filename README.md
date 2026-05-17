# flight_crawler

네이버 항공권, Google Flights, Trip.com을 실제 브라우저로 열어 항공권 검색 결과를 수집하는 프로젝트입니다.

이 프로젝트는 OpenAI API나 유료 AI 토큰을 사용하지 않습니다. Playwright가 브라우저를 직접 조작해 네이버 항공권 사이트에 접속하고, 화면에 표시되는 항공권 정보를 읽어 CSV 또는 XLSX 파일로 저장합니다.

## 주요 기능

- 출발 공항, 도착 공항, 출발일, 복귀일을 입력합니다.
- 왕복과 편도 검색을 선택할 수 있습니다.
- 네이버 항공권, Google Flights, Trip.com 중 하나를 검색하거나 `전부 검색하기`로 세 사이트를 함께 조회합니다.
- 검색 결과의 항공사, 출도착 시각, 공항 코드, 상세 경로, 가격을 수집합니다.
- 결과는 가격 오름차순으로 표시합니다.
- 가격을 클릭하면 해당 사이트의 항공권 검색/예매 화면을 새 탭으로 엽니다.
- `result/` 폴더에 결과 파일을 저장합니다.

## 설치

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m playwright install firefox
npm install
```

## 웹페이지로 실행

```bash
npm start
```

브라우저에서 아래 주소를 엽니다.

```text
http://localhost:8888
```

웹페이지에서 플랫폼, 여정 방식, 출발 공항, 도착 공항, 날짜, 수집 개수를 입력한 뒤 `가격 수집 시작`을 누르면 서버가 Python 크롤러를 실행합니다.

기본 웹 실행은 브라우저 창을 띄우지 않는 `Headless 모드`로 동작합니다. 웹페이지에서 체크를 해제하면 브라우저 창을 보면서 실행할 수 있습니다.

왕복 검색에서는 복귀일이 출발일과 같거나 더 빠른 경우 제출을 막습니다. 편도 검색에서는 복귀일 입력이 비활성화됩니다. 결과는 화면의 표에 표시되고 `result/` 폴더에 CSV로 저장됩니다.

환경에 따라 Python 실행 파일 위치가 다르면 `PYTHON_BIN`을 지정할 수 있습니다.

```bash
PYTHON_BIN=/path/to/python npm start
```

## 터미널 실행 예시

브라우저 창을 보면서 실행:

```bash
.venv/bin/python main.py --source naver --from ICN --to TPE --depart 20260517 --return-date 20260518 --items 30
```

Trip.com 편도 검색:

```bash
.venv/bin/python main.py --source trip --trip-type oneway --from ICN --to TPE --depart 20260518 --items 10 --headless
```

터미널에서 질문에 답하면서 실행:

```bash
.venv/bin/python main.py --interactive
```

엑셀로 저장:

```bash
.venv/bin/python main.py --from ICN --to SIN --depart 20260520 --return-date 20260525 --format xlsx
```

브라우저 창 없이 실행:

```bash
.venv/bin/python main.py --from ICN --to TPE --depart 20260517 --return-date 20260518 --headless
```

## 결과 파일

기본 저장 위치는 `result/`입니다.

파일명 예시:

```text
result/ICN_TO_TPE_20260517-20260518.csv
result/trip_ICN_TO_TPE_20260518-oneway.csv
```

## GitHub Pages

이 저장소에는 `public/` 폴더를 GitHub Pages로 배포하는 workflow가 포함되어 있습니다.

GitHub Pages는 정적 호스팅이므로 Python 크롤러와 Node 서버를 직접 실행하지 않습니다. 대신 GitHub Pages 화면에서 별도 API 서버 주소를 저장하면, 그 API 서버로 검색 요청을 보내 실제 크롤러를 실행할 수 있습니다.

배포된 화면:

```text
https://solishim.github.io/flight_crawler/
```

## 맥미니를 API 서버로 사용

맥미니에서 이 프로젝트 서버를 실행하고, GitHub Pages 화면은 맥미니 API 서버를 호출하는 구조로 사용할 수 있습니다.

### 가장 쉬운 실행 방법

맥미니에서 아래 파일을 더블클릭합니다.

```text
Start Flight Crawler.command
```

또는 터미널에서 아래 명령을 실행합니다.

```bash
./scripts/start-macmini-api.sh
```

스크립트가 하는 일:

1. `.flight-crawler.local.env` 파일이 없으면 API 키를 자동 생성합니다.
2. 맥미니에서 `http://127.0.0.1:8888` API 서버를 시작합니다.
3. 8888 포트가 사용 중이면 8889, 8890처럼 빈 포트를 자동으로 찾아서 사용합니다.
4. Cloudflare 임시 터널을 열고 `https://...trycloudflare.com` 주소를 만듭니다.
5. GitHub Pages 화면을 자동으로 엽니다.
6. 터미널에 API 서버 주소와 API 키를 보여줍니다.

GitHub Pages 화면이 열리면 터미널에 표시된 `API 키`를 입력하고 `저장`, `연결 확인`을 누릅니다. 이 터미널 창을 닫거나 `Ctrl-C`를 누르면 서버와 터널이 종료됩니다.

새 터널 주소로 열릴 때는 이전에 브라우저에 저장된 API 키를 자동으로 비워 둡니다. 터미널에 표시된 현재 API 키를 다시 입력해 저장하세요.

API 키 자동 입력을 켜고 싶으면 `.flight-crawler.local.env`에 아래 줄을 추가하거나 값을 바꿉니다.

```bash
AUTO_FILL_API_KEY=1
```

이 모드는 GitHub Pages를 열 때 API 키를 URL의 `#apiKey=...` fragment로 한 번 전달합니다. 웹페이지는 이 값을 `localStorage`에 저장한 뒤 주소창에서 즉시 지웁니다. `?apiKey=...`처럼 서버로 전송되지는 않지만, 화면이나 브라우저 기록에 잠깐 보일 수 있으므로 혼자 쓰는 맥미니 환경에서만 켜는 것을 권장합니다.

처음 실행할 때 `cloudflared가 설치되어 있지 않습니다`라는 메시지가 나오면 아래 명령을 한 번만 실행합니다.

```bash
brew install cloudflared
```

자동 생성되는 로컬 파일:

```text
.flight-crawler.local.env
.flight-crawler.runtime.json
.flight-crawler.logs/
```

이 파일들은 GitHub에 올라가지 않습니다.

기본 포트는 8888입니다. 이미 8888 포트가 사용 중이면 스크립트가 자동으로 다음 빈 포트를 찾아서 서버와 Cloudflare 터널을 같은 포트로 연결합니다.

특정 포트부터 찾고 싶으면 아래처럼 실행할 수 있습니다.

```bash
FLIGHT_CRAWLER_PORT=9000 ./scripts/start-macmini-api.sh
```

### 1. 맥미니에서 서버 실행

`API_KEY`는 임의의 긴 문자열로 정합니다. 이 키는 GitHub에 올리지 않고, GitHub Pages 화면의 API 키 입력칸에만 저장합니다.

```bash
API_KEY="긴_랜덤_문자열" \
ALLOWED_ORIGINS="https://solishim.github.io" \
HOST=127.0.0.1 \
PORT=8888 \
npm start
```

로컬에서 상태 확인:

```bash
curl http://127.0.0.1:8888/api/health
```

### 2. Cloudflare Tunnel 연결

GitHub Pages는 HTTPS에서 동작하므로 API 서버도 HTTPS 주소가 필요합니다. Cloudflare Tunnel을 사용하면 공유기 포트포워딩 없이 맥미니의 로컬 서버를 공개 HTTPS 주소로 연결할 수 있습니다.

Cloudflare Tunnel public hostname 예시:

```text
https://flight-api.yourdomain.com
```

Tunnel service 설정:

```text
http://127.0.0.1:8888
```

Cloudflare Tunnel을 켠 뒤 상태 확인:

```bash
curl https://flight-api.yourdomain.com/api/health
```

### 3. GitHub Pages 화면에서 API 설정

GitHub Pages 화면을 열고 `API 서버` 영역에 아래 값을 저장합니다.

```text
API 서버 주소: https://flight-api.yourdomain.com
API 키: 맥미니에서 API_KEY로 지정한 값
```

이 설정은 현재 브라우저의 `localStorage`에만 저장됩니다. 공개 저장소나 GitHub Pages 코드에는 API 키가 저장되지 않습니다.

### 4. API 보호 방식

- `API_KEY` 환경변수가 설정되면 `/api/search`는 `X-Flight-Crawler-Key` 헤더가 일치해야 실행됩니다.
- `/api/health`는 연결 확인용으로 열려 있습니다.
- `ALLOWED_ORIGINS`는 브라우저 요청을 허용할 출처입니다. GitHub Pages에서만 쓰려면 `https://solishim.github.io`를 사용합니다.
- 맥미니가 잠자기 상태가 되면 검색이 실패하므로 절전 설정을 꺼두는 것을 권장합니다.

## 주의

- 항공권 사이트의 화면 구조가 바뀌면 선택자 수정이 필요할 수 있습니다.
- 처음에는 `--headless` 없이 실행해 실제 브라우저 동작을 확인하는 것을 권장합니다.
- 너무 짧은 간격으로 반복 실행하면 사이트에서 비정상 접근으로 볼 수 있으니 천천히 사용하세요.
