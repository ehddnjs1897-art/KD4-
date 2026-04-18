#!/bin/bash
# 맥 자동 시작 설정 (launchd) — 크래시/재부팅/로그아웃 자동 복구
# 실행: bash setup_autostart.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLIST_NAME="com.claude.agent"
PLIST_PATH="$HOME/Library/LaunchAgents/$PLIST_NAME.plist"

echo "=== 자동 시작 설정 ==="

# 1. 기존 실행 중인 봇 전부 종료
echo "🛑 기존 봇 프로세스 종료..."
pkill -9 -f "python3 main.py" 2>/dev/null
pkill -9 -f "python main.py" 2>/dev/null
sleep 2

# 2. 기존 launchd 서비스 제거
echo "🧹 기존 launchd 서비스 정리..."
launchctl bootout "gui/$(id -u)/$PLIST_NAME" 2>/dev/null
launchctl unload "$PLIST_PATH" 2>/dev/null
launchctl remove "$PLIST_NAME" 2>/dev/null

mkdir -p "$HOME/Library/LaunchAgents"
mkdir -p "$SCRIPT_DIR/logs"

# 3. PATH — claude CLI 경로 포함
CLAUDE_BIN_DIR="$HOME/.npm-global/bin"
FULL_PATH="$CLAUDE_BIN_DIR:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"

cat > "$PLIST_PATH" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$PLIST_NAME</string>

    <key>ProgramArguments</key>
    <array>
        <string>$SCRIPT_DIR/.venv/bin/python3</string>
        <string>$SCRIPT_DIR/main.py</string>
    </array>

    <key>WorkingDirectory</key>
    <string>$SCRIPT_DIR</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>$FULL_PATH</string>
        <key>HOME</key>
        <string>$HOME</string>
        <key>LANG</key>
        <string>ko_KR.UTF-8</string>
    </dict>

    <key>StandardOutPath</key>
    <string>$SCRIPT_DIR/logs/agent.log</string>

    <key>StandardErrorPath</key>
    <string>$SCRIPT_DIR/logs/agent.log</string>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
        <key>Crashed</key>
        <true/>
    </dict>

    <key>ThrottleInterval</key>
    <integer>10</integer>

    <key>ProcessType</key>
    <string>Background</string>
</dict>
</plist>
EOF

# 4. 새 서비스 로드
echo "🚀 launchd 서비스 등록..."
launchctl load -w "$PLIST_PATH"

sleep 3

# 5. 상태 확인
echo ""
echo "=== 상태 확인 ==="
if launchctl list | grep -q "$PLIST_NAME"; then
    echo "✅ 서비스 등록됨"
    launchctl list | grep "$PLIST_NAME"
else
    echo "⚠️ 서비스 등록 실패 — plutil 로 plist 검증:"
    plutil "$PLIST_PATH"
fi

echo ""
echo "✅ 자동 시작 설정 완료!"
echo ""
echo "   - 맥 로그인 시 자동 시작"
echo "   - 크래시 시 10초 후 자동 재시작"
echo "   - 로그: tail -f $SCRIPT_DIR/logs/agent.log"
echo ""
echo "   수동 제어:"
echo "   중지: launchctl bootout gui/\$(id -u)/$PLIST_NAME"
echo "   시작: launchctl bootstrap gui/\$(id -u) $PLIST_PATH"
echo "   상태: launchctl list | grep $PLIST_NAME"
