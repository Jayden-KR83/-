# 외부 이동 시 실행 — Wi-Fi를 DHCP 자동으로 복원
# 우클릭 → PowerShell로 실행

$adapter = "Wi-Fi"
Write-Host "Wi-Fi DHCP 자동 설정으로 복원 중..." -ForegroundColor Cyan

netsh interface ip set address name="$adapter" dhcp
netsh interface ip set dns    name="$adapter" dhcp

Start-Sleep 3
$cur = (Get-NetIPAddress -InterfaceAlias $adapter -AddressFamily IPv4 -ErrorAction SilentlyContinue).IPAddress
Write-Host "현재 IP: $cur" -ForegroundColor Green
Write-Host "접속 주소: http://${cur}:8000  또는  http://HY005-327:8000" -ForegroundColor Yellow
