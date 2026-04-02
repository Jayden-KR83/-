"""
CDP AI Platform - Server Watchdog
pythonw.exe 로 실행: 콘솔 창 없이 백그라운드에서 uvicorn을 감시하고 재시작합니다.
Task Scheduler 에 등록되어 로그인 시 자동 실행됩니다.
"""
import subprocess
import time
import sys
import os
import socket
from pathlib import Path
from datetime import datetime

PROJECT_DIR = Path(r"C:\Project\CDP-AI-Platform")
PYTHON_EXE  = Path(sys.executable).parent / "python.exe"  # pythonw → python 자동 전환
LOG_FILE    = PROJECT_DIR / "data" / "server.log"
PORT        = 8000


def log(msg: str):
    ts   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}\n"
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line)


def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


log("=== CDP AI Platform Watchdog 시작 ===")
log(f"Python: {PYTHON_EXE}")
log(f"Project: {PROJECT_DIR}")

restart_count = 0

while True:
    # 이미 포트가 사용 중이면 대기
    if is_port_in_use(PORT):
        log(f"포트 {PORT} 이미 사용 중 — 60초 후 재확인")
        time.sleep(60)
        continue

    log(f"uvicorn 시작 (재시작 {restart_count}회)")

    try:
        # stdin/stdout/stderr 명시: pythonw.exe(콘솔 없음) 환경에서 DLL 초기화 오류(0xC0000142) 방지
        log_fd = open(LOG_FILE, "a", encoding="utf-8")
        proc = subprocess.run(
            [
                str(PYTHON_EXE),
                "-m", "uvicorn",
                "backend.main:app",
                "--host", "0.0.0.0",
                "--port", str(PORT),
                "--log-level", "info",
            ],
            cwd=str(PROJECT_DIR),
            stdin=subprocess.DEVNULL,
            stdout=log_fd,
            stderr=log_fd,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        log_fd.close()
        log(f"uvicorn 종료 (exit code: {proc.returncode})")
    except Exception as e:
        log(f"uvicorn 실행 오류: {e}")

    restart_count += 1
    log(f"5초 후 재시작... (총 {restart_count}회)")
    time.sleep(5)
