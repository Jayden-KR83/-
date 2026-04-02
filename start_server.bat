@echo off
chcp 65001 >nul
title CDP AI Platform Server

cd /d C:\Project\CDP-AI-Platform

echo ========================================
echo  CDP AI Platform - Server Starting
echo  http://localhost:8000
echo  Press Ctrl+C to stop
echo ========================================

powershell -ExecutionPolicy Bypass -File "%~dp0start_server.ps1"

pause
