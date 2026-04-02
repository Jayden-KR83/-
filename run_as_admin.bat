@echo off
chcp 65001 >nul

net session >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

echo.
echo === CDP AI Platform : Setup ===
echo.

set PYTHON=C:\Users\105415\AppData\Local\Python\pythoncore-3.14-64\python.exe
set PYTHONW=C:\Users\105415\AppData\Local\Python\pythoncore-3.14-64\pythonw.exe
set PROJECT=C:\Project\CDP-AI-Platform
set WATCHDOG=%PROJECT%\server_watchdog.py
set TASKNAME=CDP-Server

echo [1/4] Stopping existing processes...
taskkill /F /IM python.exe  >nul 2>&1
taskkill /F /IM pythonw.exe >nul 2>&1
timeout /t 2 >nul
echo      OK

echo [2/4] Adding firewall rule (port 8000)...
netsh advfirewall firewall delete rule name="CDP-8000" >nul 2>&1
netsh advfirewall firewall add rule name="CDP-8000" dir=in action=allow protocol=TCP localport=8000 profile=any
if %ERRORLEVEL% EQU 0 (
    echo      OK - Port 8000 inbound allowed
) else (
    echo      FAILED
)

echo [3/4] Registering Task Scheduler (watchdog on login)...
schtasks /delete /tn "%TASKNAME%" /f >nul 2>&1
schtasks /create /tn "%TASKNAME%" /tr "\"%PYTHONW%\" \"%WATCHDOG%\"" /sc onlogon /ru "%USERNAME%" /rl highest /f
if %ERRORLEVEL% EQU 0 (
    echo      OK - Auto-start registered
) else (
    echo      FAILED
)

echo [4/4] Starting watchdog now...
start "" "%PYTHONW%" "%WATCHDOG%"

echo      Waiting for server...
timeout /t 8 >nul

netstat -ano | findstr "0.0.0.0:8000" | findstr "LISTENING" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo.
    echo =========================================
    echo  SUCCESS!
    echo  http://localhost:8000
    echo  http://10.60.25.146:8000
    echo =========================================
) else (
    echo.
    echo  Still starting - check in 10 seconds.
    echo  Log: %PROJECT%\data\server.log
)

echo.
pause
