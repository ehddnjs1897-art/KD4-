import os
import shutil


def find_claude_binary() -> str:
    """claude CLI 절대 경로 탐색. subprocess PATH 환경 문제 회피."""
    # 1. 이미 PATH에 있으면 그대로
    found = shutil.which("claude")
    if found:
        return found

    # 2. 후보 경로들 순차 확인
    home = os.path.expanduser("~")
    candidates = [
        f"{home}/.npm-global/bin/claude",
        f"{home}/.nvm/versions/node/*/bin/claude",
        "/usr/local/bin/claude",
        "/opt/homebrew/bin/claude",
        "/usr/bin/claude",
    ]

    import glob
    for pattern in candidates:
        if "*" in pattern:
            matches = glob.glob(pattern)
            if matches:
                return matches[0]
        elif os.path.isfile(pattern) and os.access(pattern, os.X_OK):
            return pattern

    # 3. 확장된 PATH로 한 번 더 탐색
    extra_paths = [
        f"{home}/.npm-global/bin",
        "/usr/local/bin",
        "/opt/homebrew/bin",
    ]
    env_path = os.environ.get("PATH", "")
    extended = ":".join(extra_paths + [env_path])
    for d in extended.split(":"):
        candidate = os.path.join(d, "claude")
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate

    return "claude"  # fallback — subprocess가 실패하면 오류 반환


def get_subprocess_env() -> dict:
    """claude CLI 실행 시 PATH 확장한 환경 반환."""
    env = os.environ.copy()
    home = os.path.expanduser("~")
    extra = [
        f"{home}/.npm-global/bin",
        "/usr/local/bin",
        "/opt/homebrew/bin",
    ]
    current = env.get("PATH", "")
    env["PATH"] = ":".join(extra + [current])
    return env


CLAUDE_BIN = find_claude_binary()
CLAUDE_ENV = get_subprocess_env()
