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
http://localhost:8080
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

GitHub Pages는 정적 호스팅이므로 웹 UI 미리보기만 제공할 수 있습니다. Python 크롤러와 Node 서버는 Pages에서 실행되지 않습니다. 실제 검색 기능은 로컬에서 `npm start`로 서버를 실행하거나 별도의 백엔드 서버에 배포해야 사용할 수 있습니다.

## 주의

- 항공권 사이트의 화면 구조가 바뀌면 선택자 수정이 필요할 수 있습니다.
- 처음에는 `--headless` 없이 실행해 실제 브라우저 동작을 확인하는 것을 권장합니다.
- 너무 짧은 간격으로 반복 실행하면 사이트에서 비정상 접근으로 볼 수 있으니 천천히 사용하세요.
