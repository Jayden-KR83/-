@echo off
echo [CDP AI Platform] Frontend 복구 스크립트
echo.
if not exist "index.html.backup" (
    echo [오류] 백업 파일(index.html.backup)을 찾을 수 없습니다.
    pause
    exit /b 1
)
copy /Y "index.html.backup" "index.html"
echo [성공] index.html 이 백업으로 복구되었습니다.
echo 브라우저에서 Ctrl+Shift+R 을 눌러 강제 새로고침 하세요.
pause
