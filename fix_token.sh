#!/bin/bash
# 토큰 한 번에 교체 + 재시작
# 사용법: bash fix_token.sh 새토큰
# 예시:   bash fix_token.sh 7123456789:AAFxxxxxxxx

set -e

NEW_TOKEN="$1"
ENV_FILE="$(dirname "$0")/.env"

if [ -z "$NEW_TOKEN" ]; then
    echo "사용법: bash fix_token.sh 새토큰"
    exit 1
fi

echo "▶ 토큰 교체 중..."
sed -i '' "s/TELEGRAM_BOT_TOKEN=.*/TELEGRAM_BOT_TOKEN=${NEW_TOKEN}/" "$ENV_FILE" 2>/dev/null || \
sed -i    "s/TELEGRAM_BOT_TOKEN=.*/TELEGRAM_BOT_TOKEN=${NEW_TOKEN}/" "$ENV_FILE"

echo "▶ 웹훅 초기화 중..."
curl -s "https://api.telegram.org/bot${NEW_TOKEN}/deleteWebhook?drop_pending_updates=true"
echo ""

echo "▶ 구 봇 프로세스 종료..."
pkill -f "python3 main.py" 2>/dev/null || true
sleep 2

echo "▶ 봇 재시작..."
cd "$(dirname "$0")"
bash start.sh

echo "✅ 완료!"
