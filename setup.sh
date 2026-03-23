#!/bin/bash
set -e
echo "========================================"
echo " CDP AI Platform - Phase 1 환경 구축"
echo "========================================"

echo ""
echo "[Step 1] Python 버전 확인..."
python3 --version || { echo "Python3 필요"; exit 1; }

echo ""
echo "[Step 2] 가상환경 생성..."
[ ! -d "venv" ] && python3 -m venv venv
source venv/bin/activate

echo ""
echo "[Step 3] 패키지 설치..."
pip install -r requirements-minimal.txt -q

echo ""
echo "[Step 4] .env 파일 확인..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "[중요] .env 파일을 열고 ANTHROPIC_API_KEY를 입력하세요!"
    echo "  nano .env  또는  code .env"
fi

echo ""
echo "[Step 5] 자동 테스트..."
python3 backend/tests/test_phase1.py

echo ""
echo "========================================"
echo " 서버 실행"
echo "========================================"
echo "  source venv/bin/activate"
echo "  uvicorn backend.main:app --reload --port 8000"
echo ""
echo " Docker 사용:"
echo "  docker-compose up -d"
echo "========================================"
