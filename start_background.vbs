' CDP AI Platform - 창 없이 백그라운드로 서버 시작
' start_server.ps1을 숨김 창으로 실행합니다.
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "powershell.exe -WindowStyle Hidden -ExecutionPolicy Bypass -File ""C:\Project\CDP-AI-Platform\start_server.ps1""", 0, False
Set WshShell = Nothing
