# CDP AI Platform - 서버 상태 확인 및 재시작
# 언제든 실행하면 현재 상태를 보여주고, 죽어 있으면 재시작합니다.

$ProjectDir = "C:\Project\CDP-AI-Platform"
$Port       = 8000
$LogFile    = "$ProjectDir\data\server.log"

function Write-Status($msg, $color="White") { Write-Host $msg -ForegroundColor $color }

Write-Status "============================================" Cyan
Write-Status " CDP AI Platform - 서버 상태 확인" Cyan
Write-Status "============================================" Cyan

# ── 1. 포트 체크 ─────────────────────────────────────────────
$tcpClient = New-Object System.Net.Sockets.TcpClient
$connected = $false
try {
    $tcpClient.Connect("127.0.0.1", $Port)
    $connected = $true
} catch {}
$tcpClient.Close()

if ($connected) {
    Write-Status "`n✅ 서버 실행 중 (포트 $Port 응답 확인)" Green
    Write-Status "   http://localhost:$Port" Gray
    Write-Status "   http://10.60.25.146:$Port" Gray
} else {
    Write-Status "`n❌ 서버 응답 없음 - 재시작 시도 중..." Red
    # 기존 Python 프로세스 정리
    Get-Process python* -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep 1
    # 백그라운드로 재시작
    Start-Process wscript.exe -ArgumentList "`"$ProjectDir\start_background.vbs`"" -WindowStyle Hidden
    Write-Status "   재시작 명령 전송 완료. 5초 후 상태 재확인..." Yellow
    Start-Sleep 5

    $tcpClient2 = New-Object System.Net.Sockets.TcpClient
    try { $tcpClient2.Connect("127.0.0.1", $Port); $ok = $true } catch { $ok = $false }
    $tcpClient2.Close()

    if ($ok) {
        Write-Status "   ✅ 재시작 성공!" Green
    } else {
        Write-Status "   ⚠️  아직 시작 중... 잠시 후 다시 확인하세요." Yellow
    }
}

# ── 2. 프로세스 정보 ─────────────────────────────────────────
$pythonProcs = Get-Process python* -ErrorAction SilentlyContinue
if ($pythonProcs) {
    Write-Status "`nPython 프로세스:" Gray
    $pythonProcs | ForEach-Object {
        Write-Status "   PID $($_.Id)  CPU $([math]::Round($_.CPU,1))s  Mem $([math]::Round($_.WorkingSet64/1MB,0))MB" Gray
    }
}

# ── 3. 최근 로그 ─────────────────────────────────────────────
if (Test-Path $LogFile) {
    Write-Status "`n최근 로그 (마지막 5줄):" Gray
    Get-Content $LogFile -Tail 5 | ForEach-Object { Write-Status "   $_" Gray }
}

# ── 4. 작업 스케줄러 상태 ────────────────────────────────────
$task = Get-ScheduledTask -TaskName "CDP-AI-Platform-Server" -ErrorAction SilentlyContinue
if ($task) {
    Write-Status "`n작업 스케줄러: $($task.State)" $(if ($task.State -eq "Running") {"Green"} else {"Yellow"})
} else {
    Write-Status "`n⚠️  작업 스케줄러 미등록 — setup_service.ps1을 관리자로 실행하세요" Yellow
}

Write-Status "`n============================================" Cyan
Read-Host "엔터를 눌러 닫기"
