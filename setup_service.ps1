# ============================================================
# CDP AI Platform - 관리자 권한으로 1회만 실행하는 초기 설정
# 방화벽 규칙 + Windows 작업 스케줄러 등록
# ============================================================
# 실행 방법: 이 파일을 우클릭 → "관리자 권한으로 실행"

param()
$ErrorActionPreference = "Stop"

$ProjectDir  = "C:\Project\CDP-AI-Platform"
$PythonExe   = "C:\Users\105415\AppData\Local\Python\pythoncore-3.14-64\python.exe"
$TaskName    = "CDP-AI-Platform-Server"
$LogFile     = "$ProjectDir\data\server.log"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host " CDP AI Platform - 서비스 초기 설정" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

# ── 1. 방화벽 규칙 추가 ──────────────────────────────────────
Write-Host "`n[1/3] 방화벽 포트 8000 오픈 중..." -ForegroundColor Yellow

$existingRule = Get-NetFirewallRule -DisplayName "CDP AI Platform 8000" -ErrorAction SilentlyContinue
if ($existingRule) {
    Write-Host "     이미 존재 - 스킵" -ForegroundColor Gray
} else {
    New-NetFirewallRule `
        -DisplayName "CDP AI Platform 8000" `
        -Direction   Inbound `
        -Action      Allow `
        -Protocol    TCP `
        -LocalPort   8000 `
        -Profile     Any `
        -Description "CDP AI Platform FastAPI Server" | Out-Null
    Write-Host "     ✅ 방화벽 규칙 추가 완료 (TCP 8000 Inbound)" -ForegroundColor Green
}

# ── 2. 기존 스케줄 작업 삭제 ─────────────────────────────────
Write-Host "`n[2/3] 작업 스케줄러 등록 중..." -ForegroundColor Yellow

$existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existingTask) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "     기존 작업 삭제 후 재등록" -ForegroundColor Gray
}

# ── 3. 새 스케줄 작업 등록 (로그인 시 자동 시작, 창 없음) ────
$Action = New-ScheduledTaskAction `
    -Execute    "powershell.exe" `
    -Argument   "-WindowStyle Hidden -ExecutionPolicy Bypass -File `"$ProjectDir\start_server.ps1`"" `
    -WorkingDirectory $ProjectDir

# 로그인 시 + 시스템 시작 시 두 트리거 모두 등록
$TriggerLogon = New-ScheduledTaskTrigger -AtLogOn
$TriggerBoot  = New-ScheduledTaskTrigger -AtStartup

$Settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit      (New-TimeSpan -Days 365) `
    -RestartCount            5 `
    -RestartInterval         (New-TimeSpan -Minutes 1) `
    -MultipleInstances       IgnoreNew `
    -StartWhenAvailable      $true `
    -RunOnlyIfNetworkAvailable $false

# 현재 로그인 사용자로 실행 (관리자 권한 불필요)
$Principal = New-ScheduledTaskPrincipal `
    -UserId    "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType Interactive `
    -RunLevel  Highest

Register-ScheduledTask `
    -TaskName   $TaskName `
    -Action     $Action `
    -Trigger    @($TriggerLogon, $TriggerBoot) `
    -Settings   $Settings `
    -Principal  $Principal `
    -Description "CDP AI Platform FastAPI 서버 자동 시작" | Out-Null

Write-Host "     ✅ 작업 스케줄러 등록 완료" -ForegroundColor Green
Write-Host "        - 로그인 시 자동 시작" -ForegroundColor Gray
Write-Host "        - 비정상 종료 시 1분 후 자동 재시작 (최대 5회)" -ForegroundColor Gray
Write-Host "        - 창 없음 (백그라운드 실행)" -ForegroundColor Gray

# ── 4. 지금 바로 작업 시작 ───────────────────────────────────
Write-Host "`n[3/3] 서버 즉시 시작 중..." -ForegroundColor Yellow
Start-ScheduledTask -TaskName $TaskName
Start-Sleep 3

$task = Get-ScheduledTask -TaskName $TaskName
Write-Host "     작업 상태: $($task.State)" -ForegroundColor $(if ($task.State -eq "Running") {"Green"} else {"Red"})

Write-Host "`n============================================" -ForegroundColor Cyan
Write-Host " 설정 완료!" -ForegroundColor Green
Write-Host " 대시보드: http://10.60.25.146:8000" -ForegroundColor White
Write-Host " 로그 파일: $LogFile" -ForegroundColor Gray
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "`n이 창을 닫아도 서버는 계속 실행됩니다." -ForegroundColor Yellow
Read-Host "`n엔터를 눌러 닫기"
