# CDP AI Platform - Backend Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 시스템 패키지 (pdfplumber, camelot, Playwright 의존성)
RUN apt-get update && apt-get install -y \
    ghostscript \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 먼저 복사 (캐시 최적화)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Playwright Chromium 설치 (크롤링용)
RUN playwright install chromium --with-deps

# 앱 소스 복사
COPY . .

# 데이터 디렉토리 생성
RUN mkdir -p data/uploads data/outputs data/reference

# 실행 포트
EXPOSE 8000

# 서버 실행
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
