@echo off
chcp 65001 >nul
echo ========================================
echo  CDP AI Platform - Phase 1 환경 구축
echo ========================================

echo.
echo [Step 1] Python 버전 확인...
python --version 2>nul
if errorlevel 1 (
    echo [오류] Python이 없습니다. https://python.org 에서 3.11 이상 설치 후 재실행하세요.
    pause & exit /b 1
)

echo.
echo [Step 2] 가상환경 생성 및 활성화...
if not exist venv (python -m venv venv)
call venv\Scripts\activate.bat

echo.
echo [Step 3] 패키지 설치 (최소 버전)...
pip install -r requirements-minimal.txt --quiet

echo.
echo [Step 4] .env 파일 확인...
if not exist .env (
    copy .env.example .env
    echo [중요] .env 파일이 생성됐습니다.
    echo        .env 파일을 열고 ANTHROPIC_API_KEY에 실제 API Key를 입력하세요!
    notepad .env
)

echo.
echo [Step 5] 자동 테스트 실행...
python backend\tests\test_phase1.py

echo.
echo ========================================
echo  Docker 사용 방법 (선택사항)
echo ========================================
echo  Docker Desktop 설치 후:
echo    docker-compose up -d
echo  상태 확인: docker-compose ps
echo  로그 확인: docker-compose logs -f api
echo ========================================

echo.
echo [완료] 서버 실행 명령:
echo   call venv\Scripts\activate.bat
echo   uvicorn backend.main:app --reload --port 8000
echo.
echo 브라우저: http://localhost:8000/docs
pause
