#!/bin/bash
# 최소 입력 빠른 시작 — 텔레그램 메시지 한 번만 보내면 됩니다.

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
    echo -e "${RED}❌ Python3 미설치.${NC}"
    if command -v brew &>/dev/null; then
        brew install python3
    else
        echo "먼저 실행: /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        exit 1
    fi
fi

# claude CLI 확인 및 설치
echo "🤖 Claude CLI 확인 중..."
if ! command -v claude &>/dev/null; then
    echo -e "${YELLOW}Claude CLI가 없습니다. 설치 중...${NC}"
    if ! command -v npm &>/dev/null; then
        echo "Node.js 설치 중..."
        if command -v brew &>/dev/null; then
            brew install node
        else
            echo -e "${RED}❌ npm이 없습니다. https://nodejs.org 에서 Node.js를 설치하세요.${NC}"
            exit 1
        fi
    fi
    npm install -g @anthropic-ai/claude-code
    # npm 전역 설치 경로를 현재 세션 PATH에 추가
    export PATH="$(npm prefix -g)/bin:$PATH"
fi

if ! command -v claude &>/dev/null; then
    echo -e "${RED}❌ Claude CLI 설치 실패. 수동으로 실행 후 재시도:${NC}"
    echo "   npm install -g @anthropic-ai/claude-code"
    exit 1
fi
echo -e "${GREEN}✅ Claude CLI: $(claude --version 2>/dev/null || echo '설치됨')${NC}"

# Claude 로그인 확인
echo ""
echo "🔐 Claude 로그인 상태 확인..."
if ! claude -p "hi" --output-format text >/dev/null 2>&1; then
    echo -e "${YELLOW}Claude에 로그인이 필요합니다.${NC}"
    echo "브라우저가 열립니다. Max 구독 계정으로 로그인하세요."
    claude login
    if ! claude -p "hi" --output-format text >/dev/null 2>&1; then
        echo -e "${RED}❌ 로그인 실패. 다시 시도하세요.${NC}"
        exit 1
    fi
fi
echo -e "${GREEN}✅ Claude 로그인 확인${NC}"

# 가상환경 + 패키지
echo ""
echo "📦 패키지 설치 중..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate
pip install -q -r requirements.txt
echo -e "${GREEN}✅ 패키지 준비 완료${NC}"

# 봇 자동 설정
echo ""
echo "🤖 텔레그램 봇 설정 중..."
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

# .env 생성 (Anthropic API 키 불필요)
cat > .env <<EOF
TELEGRAM_BOT_TOKEN=$BOT_TOKEN
TELEGRAM_ALLOWED_USER_ID=$USER_ID
CLAUDE_MODEL=claude-opus-4-7
WORKSPACE_DIR=$HOME
DAILY_REPORT_HOUR=9
EOF
echo -e "${GREEN}✅ 설정 저장 완료${NC}"

# 맥 자동시작 등록
echo ""
echo "🔧 맥 부팅 시 자동 시작 등록 중..."
bash setup_autostart.sh

echo ""
echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}${BOLD}   완료! 에이전트 시작 중...${NC}"
echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  텔레그램 @${CYAN}${BOT_USERNAME}${NC} 에서 /start 를 눌러보세요!"
echo ""

python3 main.py
