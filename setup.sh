#!/bin/bash
# 전체 자동 셋업 스크립트
# 실행: bash setup.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
ENV_FILE="$SCRIPT_DIR/.env"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

echo ""
echo -e "${BOLD}${CYAN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${CYAN}║    Claude 자율 에이전트 — 자동 설치 마법사    ║${NC}"
echo -e "${BOLD}${CYAN}╚══════════════════════════════════════════════╝${NC}"
echo ""

# ───────────────────────────────────────────────
# 1. 필수 도구 확인
# ───────────────────────────────────────────────
echo -e "${BOLD}[1/5] 필수 도구 확인${NC}"

if ! command -v python3 &>/dev/null; then
    echo -e "  ${RED}❌ Python3 미설치.${NC}"
    if command -v brew &>/dev/null; then
        echo "  brew로 자동 설치 중..."
        brew install python3
    else
        echo -e "  ${YELLOW}먼저 Homebrew를 설치하세요: https://brew.sh${NC}"
        exit 1
    fi
fi
PY_VERSION=$(python3 --version 2>&1)
echo -e "  ${GREEN}✅ $PY_VERSION${NC}"

# ───────────────────────────────────────────────
# 2. 가상환경 + 패키지
# ───────────────────────────────────────────────
echo ""
echo -e "${BOLD}[2/5] Python 패키지 설치${NC}"

if [ ! -d ".venv" ]; then
    echo "  가상환경 생성 중..."
    python3 -m venv .venv
fi
source .venv/bin/activate

echo "  패키지 설치 중 (최초 1~2분 소요)..."
pip install -q -r requirements.txt
echo -e "  ${GREEN}✅ 패키지 설치 완료${NC}"

# ───────────────────────────────────────────────
# 3. Anthropic API 키
# ───────────────────────────────────────────────
echo ""
echo -e "${BOLD}[3/5] Anthropic API 키 설정${NC}"
echo -e "  ${YELLOW}→ https://console.anthropic.com 에서 발급${NC}"
echo -n "  Anthropic API Key: "
read -r ANTHROPIC_KEY
if [ -z "$ANTHROPIC_KEY" ]; then
    echo -e "  ${RED}❌ API 키를 입력해야 합니다.${NC}"; exit 1
fi
echo -e "  ${GREEN}✅ API 키 입력됨${NC}"

# ───────────────────────────────────────────────
# 4. 텔레그램 봇 설정
# ───────────────────────────────────────────────
echo ""
echo -e "${BOLD}[4/5] 텔레그램 봇 설정${NC}"
echo ""
echo -e "  ${YELLOW}지금 텔레그램 앱에서 아래를 따라하세요:${NC}"
echo "  ① 텔레그램 검색창에 @BotFather 검색"
echo "  ② /newbot 입력"
echo "  ③ 봇 이름 입력 (예: 내Claude에이전트)"
echo "  ④ 봇 username 입력 (영어, _bot으로 끝나야 함, 예: myagent_bot)"
echo "  ⑤ BotFather가 주는 토큰 복사 (예: 1234567890:ABCdef...)"
echo ""
echo -n "  텔레그램 봇 토큰: "
read -r BOT_TOKEN
if [ -z "$BOT_TOKEN" ]; then
    echo -e "  ${RED}❌ 봇 토큰을 입력해야 합니다.${NC}"; exit 1
fi

echo ""
echo "  봇 프로필 자동 설정 중..."
python3 setup_telegram.py "$BOT_TOKEN"
if [ $? -ne 0 ]; then
    echo -e "  ${RED}❌ 봇 토큰이 올바르지 않습니다.${NC}"; exit 1
fi
echo -e "  ${GREEN}✅ 봇 설정 완료${NC}"

# ───────────────────────────────────────────────
# 5. 내 Telegram User ID 자동 캡처
# ───────────────────────────────────────────────
echo ""
echo -e "${BOLD}[5/5] 내 Telegram User ID 자동 캡처${NC}"
echo ""
echo -e "  ${YELLOW}방금 만든 봇에게 텔레그램에서 아무 메시지나 보내주세요.${NC}"
echo "  (60초 대기, 먼저 봇 링크 클릭 후 /start 또는 '안녕' 전송)"
echo ""

CAPTURE_OUTPUT=$(python3 get_my_id.py "$BOT_TOKEN" 2>&1)
USER_ID=$(echo "$CAPTURE_OUTPUT" | grep "CAPTURED_ID=" | cut -d= -f2)

if [ -z "$USER_ID" ] || [ "$USER_ID" = "0" ]; then
    echo -e "  ${YELLOW}⚠ 자동 캡처 실패. User ID를 직접 입력하세요.${NC}"
    echo "  (@userinfobot 에 메시지 보내면 확인 가능)"
    echo -n "  Telegram User ID: "
    read -r USER_ID
fi

if [ -z "$USER_ID" ]; then
    echo -e "  ${RED}❌ User ID를 입력해야 합니다.${NC}"; exit 1
fi
echo -e "  ${GREEN}✅ User ID: $USER_ID${NC}"

# ───────────────────────────────────────────────
# .env 파일 작성
# ───────────────────────────────────────────────
cat > "$ENV_FILE" <<EOF
TELEGRAM_BOT_TOKEN=$BOT_TOKEN
TELEGRAM_ALLOWED_USER_ID=$USER_ID
ANTHROPIC_API_KEY=$ANTHROPIC_KEY
CLAUDE_MODEL=claude-opus-4-7
WORKSPACE_DIR=~
DAILY_REPORT_HOUR=9
EOF

echo ""
echo -e "${GREEN}${BOLD}╔══════════════════════════════════════╗${NC}"
echo -e "${GREEN}${BOLD}║         설치 완료!                   ║${NC}"
echo -e "${GREEN}${BOLD}╚══════════════════════════════════════╝${NC}"
echo ""
echo "  에이전트 시작:       bash start.sh"
echo "  맥 자동시작 설정:    bash setup_autostart.sh"
echo "  로그 보기:           tail -f logs/agent.log"
echo ""
echo -e "  텔레그램 봇에서 ${CYAN}/start${NC} 를 보내 시작하세요!"
echo ""

# 바로 시작할지 묻기
echo -n "  지금 바로 에이전트를 시작할까요? [Y/n] "
read -r START_NOW
if [[ "$START_NOW" =~ ^[Nn]$ ]]; then
    echo "  나중에 'bash start.sh' 로 시작하세요."
else
    echo ""
    bash start.sh
fi
