#!/bin/bash
# 맥 부팅 시 자동 시작 설정 (launchd)
# 실행: bash setup_autostart.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLIST_NAME="com.claude.agent"
PLIST_PATH="$HOME/Library/LaunchAgents/$PLIST_NAME.plist"

echo "=== 자동 시작 설정 ==="

mkdir -p "$HOME/Library/LaunchAgents"

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
        <string>/usr/local/bin:/usr/bin:/bin</string>
    </dict>

    <key>StandardOutPath</key>
    <string>$SCRIPT_DIR/logs/agent.log</string>

    <key>StandardErrorPath</key>
    <string>$SCRIPT_DIR/logs/agent.log</string>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
EOF

mkdir -p "$SCRIPT_DIR/logs"

# 기존 서비스 언로드 (있으면)
launchctl unload "$PLIST_PATH" 2>/dev/null

# 새 서비스 로드
launchctl load "$PLIST_PATH"

echo "✅ 자동 시작 설정 완료!"
echo "   맥 재시작 후 자동으로 에이전트가 켜집니다."
echo ""
echo "   수동 제어:"
echo "   중지: launchctl unload ~/Library/LaunchAgents/$PLIST_NAME.plist"
echo "   시작: launchctl load ~/Library/LaunchAgents/$PLIST_NAME.plist"
echo "   로그: tail -f $SCRIPT_DIR/logs/agent.log"
