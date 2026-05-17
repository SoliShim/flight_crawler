#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

CONFIG_FILE="${FLIGHT_CRAWLER_CONFIG:-$ROOT_DIR/.flight-crawler.local.env}"
RUNTIME_FILE="$ROOT_DIR/.flight-crawler.runtime.json"
LOG_DIR="$ROOT_DIR/.flight-crawler.logs"
SERVER_LOG="$LOG_DIR/server.log"
TUNNEL_LOG="$LOG_DIR/cloudflared.log"
PAGES_URL="${PAGES_URL:-https://solishim.github.io/flight_crawler/}"

mkdir -p "$LOG_DIR"

generate_key() {
  if command -v openssl >/dev/null 2>&1; then
    openssl rand -hex 24
  else
    date "+flight-crawler-%Y%m%d%H%M%S"
  fi
}

write_default_config() {
  local generated_key
  generated_key="$(generate_key)"
  cat > "$CONFIG_FILE" <<EOF
API_KEY="$generated_key"
ALLOWED_ORIGINS="https://solishim.github.io"
HOST=127.0.0.1
PORT=8080
EOF
  chmod 600 "$CONFIG_FILE"
}

if [ ! -f "$CONFIG_FILE" ]; then
  write_default_config
fi

set -a
# shellcheck disable=SC1090
. "$CONFIG_FILE"
set +a

API_KEY="${API_KEY:-$(generate_key)}"
ALLOWED_ORIGINS="${ALLOWED_ORIGINS:-https://solishim.github.io}"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8080}"

if ! command -v npm >/dev/null 2>&1; then
  echo "npm을 찾을 수 없습니다. Node.js를 먼저 설치해 주세요."
  exit 1
fi

if ! command -v cloudflared >/dev/null 2>&1; then
  echo "cloudflared가 설치되어 있지 않습니다."
  echo "먼저 아래 명령을 한 번 실행해 주세요:"
  echo
  echo "  brew install cloudflared"
  echo
  exit 1
fi

SERVER_PID=""
TUNNEL_PID=""
STARTED_SERVER=0

cleanup() {
  echo
  echo "Flight Crawler 서버를 종료합니다."
  if [ -n "${TUNNEL_PID:-}" ] && kill -0 "$TUNNEL_PID" >/dev/null 2>&1; then
    kill "$TUNNEL_PID" >/dev/null 2>&1 || true
  fi
  if [ "$STARTED_SERVER" = "1" ] && [ -n "${SERVER_PID:-}" ] && kill -0 "$SERVER_PID" >/dev/null 2>&1; then
    kill "$SERVER_PID" >/dev/null 2>&1 || true
  fi
}

trap cleanup INT TERM EXIT

health_url="http://$HOST:$PORT/api/health"

if curl -fsS "$health_url" >/dev/null 2>&1; then
  if [ "${FLIGHT_CRAWLER_REUSE_SERVER:-0}" != "1" ]; then
    echo "이미 $health_url 에 서버가 실행 중입니다."
    echo "API 키가 현재 스크립트 설정과 다를 수 있으므로 자동 실행을 중단합니다."
    echo
    echo "해결 방법:"
    echo "1. 기존 서버 터미널을 종료한 뒤 이 파일을 다시 실행합니다."
    echo "2. 기존 서버를 그대로 쓰려면 아래처럼 실행합니다."
    echo "   FLIGHT_CRAWLER_REUSE_SERVER=1 ./scripts/start-macmini-api.sh"
    exit 1
  fi
  echo "이미 실행 중인 로컬 API 서버를 재사용합니다: $health_url"
else
  echo "맥미니 로컬 API 서버를 시작합니다..."
  : > "$SERVER_LOG"
  API_KEY="$API_KEY" \
  ALLOWED_ORIGINS="$ALLOWED_ORIGINS" \
  HOST="$HOST" \
  PORT="$PORT" \
  npm start > "$SERVER_LOG" 2>&1 &
  SERVER_PID="$!"
  STARTED_SERVER=1

  for _ in $(seq 1 60); do
    if curl -fsS "$health_url" >/dev/null 2>&1; then
      break
    fi
    sleep 1
  done

  if ! curl -fsS "$health_url" >/dev/null 2>&1; then
    echo "로컬 API 서버가 시작되지 않았습니다. 로그를 확인해 주세요:"
    echo "$SERVER_LOG"
    exit 1
  fi
fi

echo "Cloudflare 임시 터널을 시작합니다..."
: > "$TUNNEL_LOG"
cloudflared tunnel --url "http://$HOST:$PORT" --no-autoupdate > "$TUNNEL_LOG" 2>&1 &
TUNNEL_PID="$!"

TUNNEL_URL=""
for _ in $(seq 1 60); do
  TUNNEL_URL="$(grep -Eo 'https://[-a-zA-Z0-9.]+\.trycloudflare\.com' "$TUNNEL_LOG" | tail -n 1 || true)"
  if [ -n "$TUNNEL_URL" ]; then
    break
  fi
  sleep 1
done

if [ -z "$TUNNEL_URL" ]; then
  echo "Cloudflare 터널 주소를 찾지 못했습니다. 로그를 확인해 주세요:"
  echo "$TUNNEL_LOG"
  exit 1
fi

cat > "$RUNTIME_FILE" <<EOF
{
  "apiBase": "$TUNNEL_URL",
  "apiKey": "$API_KEY",
  "localHealthUrl": "$health_url",
  "pagesUrl": "$PAGES_URL"
}
EOF
chmod 600 "$RUNTIME_FILE"

echo
echo "준비가 끝났습니다."
echo
echo "1. GitHub Pages 화면"
echo "   $PAGES_URL?apiBase=$TUNNEL_URL"
echo
echo "2. API 서버 주소"
echo "   $TUNNEL_URL"
echo
echo "3. API 키"
echo "   $API_KEY"
echo
echo "열린 GitHub Pages 화면에서 API 키를 입력하고 저장한 뒤, 연결 확인을 누르세요."
echo "이 창을 닫거나 Ctrl-C를 누르면 맥미니 서버와 터널이 종료됩니다."
echo

if command -v open >/dev/null 2>&1; then
  open "$PAGES_URL?apiBase=$TUNNEL_URL" || true
fi

while true; do
  if [ "$STARTED_SERVER" = "1" ] && ! kill -0 "$SERVER_PID" >/dev/null 2>&1; then
    echo "로컬 API 서버가 종료되었습니다. 로그: $SERVER_LOG"
    exit 1
  fi
  if ! kill -0 "$TUNNEL_PID" >/dev/null 2>&1; then
    echo "Cloudflare 터널이 종료되었습니다. 로그: $TUNNEL_LOG"
    exit 1
  fi
  sleep 2
done
