# CDP AI Platform - Task Scheduler 등록
# 관리자 권한 없이 현재 사용자 로그인 시 자동 시작

$TaskName    = "CDP-AI-Platform-Watchdog"
$PythonwExe  = "C:\Users\105415\AppData\Local\Python\pythoncore-3.14-64\pythonw.exe"
$ScriptPath  = "C:\Project\CDP-AI-Platform\server_watchdog.py"
$WorkDir     = "C:\Project\CDP-AI-Platform"
$LogFile     = "C:\Project\CDP-AI-Platform\data\server.log"

# 기존 작업 제거
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

$Action  = New-ScheduledTaskAction `
    -Execute $PythonwExe `
    -Argument $ScriptPath `
    -WorkingDirectory $WorkDir

# 로그인 시 실행 (현재 사용자)
$Trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME

$Settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Hours 0) `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -MultipleInstances IgnoreNew

$Principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType Interactive `
    -RunLevel Limited

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Principal $Principal `
    -Description "CDP AI Platform 서버 자동 시작 (watchdog)" `
    -Force

Write-Host "Task '$TaskName' 등록 완료."
Write-Host "다음 로그인부터 자동 시작됩니다."
