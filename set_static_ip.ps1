# 근무지 복귀 시 실행 — Wi-Fi를 10.60.25.146 고정 IP로 설정
# 우클릭 → PowerShell로 실행

$adapter = "Wi-Fi"
$ip      = "10.60.25.146"
$mask    = 23          # 255.255.254.0
$gateway = "10.60.28.1"
$dns1    = "203.235.244.41"
$dns2    = "203.235.244.42"

Write-Host "Wi-Fi 고정 IP 설정 중: $ip" -ForegroundColor Cyan

netsh interface ip set address name="$adapter" static $ip 255.255.254.0 $gateway
netsh interface ip set dns    name="$adapter" static $dns1
netsh interface ip add dns    name="$adapter" $dns2 index=2

Start-Sleep 2
$cur = (Get-NetIPAddress -InterfaceAlias $adapter -AddressFamily IPv4 -ErrorAction SilentlyContinue).IPAddress
Write-Host "현재 IP: $cur" -ForegroundColor Green
Write-Host "접속 주소: http://${ip}:8000" -ForegroundColor Yellow
