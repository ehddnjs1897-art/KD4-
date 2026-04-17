#!/bin/bash
# 최소 입력 빠른 시작 — Anthropic API 키만 입력하면 됩니다.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

BOT_TOKEN="8447264457:AAFOyeah4PmLX6x6ADJM6_yz2B1MUW78mjA"
BOT_USERNAME="kd3agentic_bot"

CYAN='\033[0;36m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; BOLD='\033[1m'; NC='\033[0m'

echo ""
echo -e "${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}${CYAN}   Claude 자율 에이전트 — 빠른 시작${NC}"
echo -e "${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Python 확인
if ! command -v python3 &>/dev/null; then
    echo -e "${RED}❌ Python3 미설치. 먼저 실행: brew install python3${NC}"
    exit 1
fi

# 가상환경 + 패키지
if [ ! -d ".venv" ]; then
    echo "📦 가상환경 생성 중..."
    python3 -m venv .venv
fi
source .venv/bin/activate
echo "📦 패키지 설치 중..."
pip install -q -r requirements.txt
echo -e "${GREEN}✅ 패키지 준비 완료${NC}"
echo ""

# Anthropic API 키만 입력받기
echo -e "${YELLOW}▶ Anthropic API Key를 입력하세요${NC}"
echo "  (https://console.anthropic.com → API Keys)"
echo -n "  API Key: "
read -r ANTHROPIC_KEY
if [ -z "$ANTHROPIC_KEY" ]; then
    echo -e "${RED}❌ API 키가 필요합니다.${NC}"; exit 1
fi

# 봇 자동 설정
echo ""
echo "🤖 봇 설정 중..."
python3 setup_telegram.py "$BOT_TOKEN"

# User ID 자동 캡처
echo ""
echo -e "${YELLOW}▶ 지금 텔레그램에서 @${BOT_USERNAME} 에게 아무 메시지나 보내주세요 (60초 대기)${NC}"
echo ""
CAPTURE_OUT=$(python3 get_my_id.py "$BOT_TOKEN" 2>&1)
USER_ID=$(echo "$CAPTURE_OUT" | grep "CAPTURED_ID=" | cut -d= -f2)

if [ -z "$USER_ID" ] || [ "$USER_ID" = "0" ]; then
    echo -e "${YELLOW}⚠ 자동 캡처 실패. @userinfobot 에게 메시지 보내서 ID 확인 후 입력하세요.${NC}"
    echo -n "  Telegram User ID: "
    read -r USER_ID
fi
echo -e "${GREEN}✅ User ID: $USER_ID${NC}"

# .env 생성
cat > .env <<EOF
TELEGRAM_BOT_TOKEN=$BOT_TOKEN
TELEGRAM_ALLOWED_USER_ID=$USER_ID
ANTHROPIC_API_KEY=$ANTHROPIC_KEY
CLAUDE_MODEL=claude-opus-4-7
WORKSPACE_DIR=~
DAILY_REPORT_HOUR=9
EOF
echo -e "${GREEN}✅ .env 저장 완료${NC}"

# 맥 자동시작 등록
echo ""
echo "🔧 맥 부팅 시 자동 시작 등록 중..."
bash setup_autostart.sh

echo ""
echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}${BOLD}   완료! 에이전트가 백그라운드에서 실행 중입니다.${NC}"
echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  텔레그램 @${CYAN}${BOT_USERNAME}${NC} 에서 /start 를 눌러 시작하세요!"
echo ""
echo "  로그 확인: tail -f $SCRIPT_DIR/logs/agent.log"
echo ""

# 바로 실행
python3 main.py
