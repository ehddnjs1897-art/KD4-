#!/bin/bash
# 맥에서 더블클릭 또는 터미널에서 실행: bash start.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Claude 자율 에이전트 시작 ==="

# .env 파일 확인
if [ ! -f ".env" ]; then
    echo "❌ .env 파일이 없습니다."
    echo "   .env.example을 복사해서 .env를 만들고 값을 채워주세요:"
    echo "   cp .env.example .env"
    exit 1
fi

# Python 확인
if ! command -v python3 &>/dev/null; then
    echo "❌ Python3가 설치되지 않았습니다."
    echo "   brew install python3 로 설치하세요."
    exit 1
fi

# 가상환경 설정 (없으면 생성)
if [ ! -d ".venv" ]; then
    echo "📦 가상환경 생성 중..."
    python3 -m venv .venv
fi

source .venv/bin/activate

# 패키지 설치
echo "📦 패키지 확인 중..."
pip install -q -r requirements.txt

echo "🚀 에이전트 서버 시작!"
echo "   텔레그램에서 봇에게 /start 를 보내보세요."
echo "   종료: Ctrl+C"
echo ""

python3 main.py
