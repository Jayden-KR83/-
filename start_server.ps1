# CDP AI Platform - 서버 자동 재시작 데몬
# start_background.vbs 또는 작업 스케줄러가 이 파일을 숨김 창으로 실행합니다.

$ProjectDir = "C:\Project\CDP-AI-Platform"
$PythonExe  = "C:\Users\105415\AppData\Local\Python\pythoncore-3.14-64\python.exe"
$LogFile    = "$ProjectDir\data\server.log"
$PidFile    = "$ProjectDir\data\server.pid"

Set-Location $ProjectDir

function Write-Log($msg) {
    $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $msg"
    Write-Host $line
    Add-Content -Path $LogFile -Value $line -Encoding UTF8
}

Write-Log "=== CDP AI Platform 서버 시작 ==="
Write-Log "Python: $PythonExe"
Write-Log "Project: $ProjectDir"

$restartCount = 0

# 무한 루프: 어떤 이유로 꺼져도 항상 재시작
while ($true) {
    Write-Log "uvicorn 시작 (재시작 $restartCount 회)..."

    $proc = Start-Process $PythonExe `
        -ArgumentList "-m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --log-level info" `
        -WorkingDirectory $ProjectDir `
        -PassThru -NoNewWindow

    $proc.Id | Set-Content $PidFile -Encoding UTF8
    Write-Log "서버 PID: $($proc.Id) | http://0.0.0.0:8000 | http://10.60.25.146:8000"

    $proc.WaitForExit()

    Remove-Item $PidFile -ErrorAction SilentlyContinue
    $restartCount++
    Write-Log "서버 종료됨. 5초 후 재시작... (총 $restartCount 회)"
    Start-Sleep 5
}
