# CDP AI Platform — Phase 1 설치 가이드

## 구성 요소
| 컴포넌트 | 역할 | 비고 |
|----------|------|------|
| FastAPI 백엔드 | PDF 파싱, 크롤링, API 서버 | Python 3.11+ |
| Claude API | AI 분석 및 보정 | Anthropic 유료 API |
| Playwright | JS 동적 페이지 크롤링 | Chromium 사용 |
| Docker Compose | 로컬 서버 운영 | 선택 사항 |

---

## 🔴 보안 체크리스트 (IT팀 검토용)

| 항목 | 내용 | 조치 |
|------|------|------|
| API Key 관리 | .env 파일에만 저장, Git 미포함 | .gitignore 적용 완료 |
| 외부 데이터 전송 | CDP 답변 내용이 Anthropic 서버로 전송됨 | **담당팀 보안 정책 확인 필요** |
| 크롤링 대상 | 허용 도메인 목록 사전 정의 | crawling_guide.skill.md 참조 |
| 포트 오픈 | 8000번 (로컬만) | 외부 방화벽 불필요 |
| 설치 소프트웨어 | Python, Docker Desktop | IT팀 사전 승인 필요 |

> **핵심 주의**: Claude API를 사용할 경우 CDP 응답 데이터가
> Anthropic 서버(미국)로 전송됩니다. 전송 전 개인정보·영업비밀
> 포함 여부를 반드시 확인하고, 필요 시 데이터 마스킹을 적용하세요.
> Anthropic의 데이터 보호 정책: https://www.anthropic.com/privacy

---

## Step 1: Anthropic API Key 발급
1. https://console.anthropic.com 접속 (계정 필요)
2. API Keys → Create Key
3. 키 복사 (sk-ant-... 형식)

---

## Step 2: 프로젝트 설정

### 방법 A: 직접 실행 (Python)
```bash
# Windows
setup_windows.bat

# Mac/Linux
./setup.sh
```

### 방법 B: Docker (권장)
```bash
# .env 파일 생성
cp .env.example .env
# .env 파일에 ANTHROPIC_API_KEY 입력

# Docker Compose 실행
docker-compose up -d

# 상태 확인
docker-compose ps
curl http://localhost:8000/api/v1/health
```

---

## Step 3: API Key 설정
```bash
# .env 파일 편집
ANTHROPIC_API_KEY=sk-ant-여기에_실제_키_입력
CLAUDE_MODEL=claude-sonnet-4-5
```

---

## Step 4: 테스트
```bash
# 자동 테스트 (10개 항목)
python backend/tests/test_phase1.py
# → 결과: 10개 통과 / 0개 실패

# API 상태 확인
curl http://localhost:8000/api/v1/health
```

---

## Step 5: VS Code + Claude Code 연동
1. VS Code에서 `cdp-ai-platform` 폴더 열기
2. Claude Code 확장 설치 (Extensions → "Claude Code")
3. `CLAUDE.md`가 루트에 있으면 Claude Code가 자동으로 프로젝트 지시문 인식
4. Claude Code에서: `"Phase 2 채점 Agent 구현해줘"` → SKILL.md 참조해 자동 구현

---

## API 사용 예시

### PDF 파싱
```bash
curl -X POST http://localhost:8000/api/v1/parse-pdf \
  -F "file=@cdp_guide_2024.pdf"
```

### 웹 크롤링
```bash
curl -X POST http://localhost:8000/api/v1/crawl \
  -H "Content-Type: application/json" \
  -d '{
    "urls": ["https://cdp.net/en/guidance"],
    "query": "CDP 2024 채점 기준 변경사항",
    "summarize": true
  }'
```

### Swagger UI (브라우저에서 직접 테스트)
http://localhost:8000/docs

---

## SKILL.md 업데이트 방법
채점 기준이 변경될 때 코드 수정 없이:
```bash
# skills/scoring_criteria.skill.md 파일만 편집
# Docker 사용 시: 재빌드 불필요 (볼륨 마운트)
# 일반 실행 시: 서버 재시작 불필요 (런타임 로드)
```

---

## 자주 묻는 문제

**Q: API Key 인증 오류**
→ .env 파일에 키가 올바르게 입력됐는지 확인 (sk-ant-로 시작)

**Q: Docker 실행 오류**
→ Docker Desktop이 실행 중인지 확인: `docker ps`

**Q: playwright 설치 오류**
→ `playwright install chromium` 별도 실행 (또는 Docker 사용)

**Q: camelot 설치 오류**
→ `pip install -r requirements-minimal.txt` 사용 (camelot 제외)
