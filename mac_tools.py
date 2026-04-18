import os
import subprocess
from pathlib import Path
from datetime import datetime


def run_applescript(script: str, timeout: int = 30) -> str:
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=timeout
        )
        out = result.stdout.strip()
        err = result.stderr.strip()
        if err and not out:
            return f"AppleScript 오류: {err[:500]}"
        return out or "(결과 없음)"
    except subprocess.TimeoutExpired:
        return f"AppleScript 시간 초과 ({timeout}s)"
    except FileNotFoundError:
        return "osascript 미설치 (Mac 아님)"


def mac_notify(title: str, message: str) -> str:
    safe_title = title.replace('"', "'")[:80]
    safe_msg = message.replace('"', "'")[:200]
    script = f'display notification "{safe_msg}" with title "{safe_title}"'
    run_applescript(script, timeout=5)
    return f"알림 전송: {title}"


def mac_say(text: str, voice: str = "Yuna") -> str:
    safe = text.replace('"', "'")[:500]
    try:
        subprocess.run(["say", "-v", voice, safe], timeout=30, check=False)
        return f"음성 출력 완료 ({voice}): {safe[:60]}"
    except subprocess.TimeoutExpired:
        return "음성 출력 시간 초과"
    except FileNotFoundError:
        return "say 명령 없음 (Mac 아님)"


def mac_clipboard_read() -> str:
    try:
        result = subprocess.run(["pbpaste"], capture_output=True, text=True, timeout=5)
        return result.stdout or "(클립보드 비어있음)"
    except Exception as e:
        return f"클립보드 읽기 실패: {e}"


def mac_clipboard_write(text: str) -> str:
    try:
        subprocess.run(["pbcopy"], input=text, text=True, timeout=5, check=False)
        return f"클립보드에 저장됨 ({len(text)}자)"
    except Exception as e:
        return f"클립보드 쓰기 실패: {e}"


def mac_screenshot(path: str = "") -> str:
    if not path:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.expanduser(f"~/Desktop/screenshot_{ts}.png")
    else:
        path = os.path.expanduser(path)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(["screencapture", "-x", path], timeout=10, check=True)
        return path
    except Exception as e:
        return f"스크린샷 실패: {e}"


def system_info() -> str:
    lines = []
    try:
        bat = subprocess.run(
            ["pmset", "-g", "batt"], capture_output=True, text=True, timeout=5
        ).stdout
        for l in bat.splitlines():
            if "%" in l:
                lines.append(f"🔋 {l.strip()}")
                break
    except Exception:
        pass

    try:
        df = subprocess.run(
            ["df", "-h", "/"], capture_output=True, text=True, timeout=5
        ).stdout.splitlines()
        if len(df) > 1:
            parts = df[1].split()
            if len(parts) >= 5:
                lines.append(f"💾 디스크: {parts[2]} / {parts[1]} ({parts[4]} 사용)")
    except Exception:
        pass

    try:
        mem = subprocess.run(
            ["vm_stat"], capture_output=True, text=True, timeout=5
        ).stdout
        free_pages = 0
        for l in mem.splitlines():
            if l.startswith("Pages free:"):
                free_pages = int(l.split(":")[1].strip().rstrip("."))
                break
        free_gb = free_pages * 4096 / (1024**3)
        lines.append(f"🧠 여유 메모리: {free_gb:.1f} GB")
    except Exception:
        pass

    try:
        load = os.getloadavg()
        lines.append(f"⚙️ CPU 부하: {load[0]:.2f} / {load[1]:.2f} / {load[2]:.2f}")
    except Exception:
        pass

    try:
        uptime = subprocess.run(
            ["uptime"], capture_output=True, text=True, timeout=5
        ).stdout.strip()
        lines.append(f"⏱ {uptime}")
    except Exception:
        pass

    return "\n".join(lines) if lines else "시스템 정보 가져오기 실패"


def mac_mail_unread() -> str:
    script = '''
    tell application "Mail"
        set unreadCount to unread count of inbox
        set msgList to {}
        set msgs to messages of inbox
        repeat with i from 1 to (count of msgs)
            if i > 5 then exit repeat
            set m to item i of msgs
            if read status of m is false then
                set end of msgList to (subject of m) & " — " & (sender of m)
            end if
        end repeat
        return (unreadCount as string) & "\n" & (msgList as string)
    end tell
    '''
    return run_applescript(script, timeout=15)


def mac_calendar_today() -> str:
    script = '''
    set today to current date
    set startT to today - (time of today)
    set endT to startT + (24 * 60 * 60)
    set eventList to {}
    tell application "Calendar"
        repeat with cal in calendars
            set evs to (every event of cal whose start date ≥ startT and start date < endT)
            repeat with ev in evs
                set end of eventList to (summary of ev) & " @ " & ((start date of ev) as string)
            end repeat
        end repeat
    end tell
    return eventList as string
    '''
    return run_applescript(script, timeout=30)


def mac_open_app(app_name: str) -> str:
    safe = app_name.replace('"', "'")[:80]
    try:
        subprocess.run(["open", "-a", safe], timeout=10, check=True)
        return f"앱 열림: {safe}"
    except Exception as e:
        return f"앱 열기 실패: {e}"
