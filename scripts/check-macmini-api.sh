#!/usr/bin/env bash
set -u

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

CONFIG_FILE="${FLIGHT_CRAWLER_CONFIG:-$ROOT_DIR/.flight-crawler.local.env}"
RUNTIME_FILE="$ROOT_DIR/.flight-crawler.runtime.json"
LOG_DIR="$ROOT_DIR/.flight-crawler.logs"
SERVER_LOG="$LOG_DIR/server.log"
TUNNEL_LOG="$LOG_DIR/cloudflared.log"

if [ -f "$CONFIG_FILE" ]; then
  set -a
  # shellcheck disable=SC1090
  . "$CONFIG_FILE"
  set +a
fi

HOST="${HOST:-127.0.0.1}"
PORT="${FLIGHT_CRAWLER_PORT:-${PORT:-8888}}"
LOCAL_HEALTH_URL="http://$HOST:$PORT/api/health"
PUBLIC_HEALTH_URL=""

read_runtime_field() {
  local field="$1"

  if [ ! -f "$RUNTIME_FILE" ] || ! command -v node >/dev/null 2>&1; then
    return 0
  fi

  node -e '
const fs = require("fs");
const file = process.argv[1];
const field = process.argv[2];
try {
  const data = JSON.parse(fs.readFileSync(file, "utf8"));
  if (typeof data[field] === "string") {
    process.stdout.write(data[field]);
  }
} catch (_) {}
' "$RUNTIME_FILE" "$field" 2>/dev/null
}

runtime_local_health_url="$(read_runtime_field localHealthUrl)"
runtime_api_base="$(read_runtime_field apiBase)"

if [ -n "$runtime_local_health_url" ]; then
  LOCAL_HEALTH_URL="$runtime_local_health_url"
fi

if [ -n "${1:-}" ]; then
  case "$1" in
    */api/health) PUBLIC_HEALTH_URL="$1" ;;
    *) PUBLIC_HEALTH_URL="${1%/}/api/health" ;;
  esac
elif [ -n "$runtime_api_base" ]; then
  PUBLIC_HEALTH_URL="${runtime_api_base%/}/api/health"
fi

check_health() {
  local label="$1"
  local url="$2"
  local response

  response="$(curl -fsS --max-time 8 "$url" 2>/dev/null)"
  local curl_status=$?

  if [ "$curl_status" -ne 0 ]; then
    echo "실패: ${label}가 응답하지 않습니다."
    echo "  주소: $url"
    return 1
  fi

  if ! printf '%s' "$response" | grep -q '"ok"[[:space:]]*:[[:space:]]*true'; then
    echo "실패: $label 응답은 받았지만 health 응답이 아닙니다."
    echo "  주소: $url"
    echo "  응답: $response"
    return 1
  fi

  echo "정상: $label"
  echo "  주소: $url"
  echo "  응답: $response"
  return 0
}

echo "Flight Crawler 서버 상태 확인"
echo

status=0

if ! check_health "로컬 API 서버" "$LOCAL_HEALTH_URL"; then
  status=1
fi

echo

if [ -n "$PUBLIC_HEALTH_URL" ]; then
  if ! check_health "외부 터널 API 서버" "$PUBLIC_HEALTH_URL"; then
    status=1
  fi
else
  echo "건너뜀: 외부 터널 주소를 찾지 못했습니다."
  echo "  $RUNTIME_FILE 파일이 없으면 ./scripts/start-macmini-api.sh 를 먼저 실행하세요."
  echo "  특정 주소를 직접 확인하려면 ./scripts/check-macmini-api.sh https://...trycloudflare.com 처럼 실행하세요."
fi

echo

if [ "$status" -eq 0 ]; then
  echo "결과: 서버가 실행 중이고 health 응답이 정상입니다."
else
  echo "결과: 서버 상태 확인에 실패했습니다."
  if [ -f "$SERVER_LOG" ]; then
    echo "  로컬 서버 로그: $SERVER_LOG"
  fi
  if [ -f "$TUNNEL_LOG" ]; then
    echo "  터널 로그: $TUNNEL_LOG"
  fi
fi

exit "$status"
