# Session Log — Phase 2 완성 + 서버 영구화 + Hooks 설정

> 작성일: 2026-03-26
> 이 문서는 컨텍스트 clear 전 세션 전체 작업 내용을 보존하기 위한 기록입니다.

---

## 1. 이번 세션에서 완료된 작업 목록

| # | 작업 | 상태 |
|---|---|---|
| 1 | Phase 2 CDP 워크벤치 COL_MAP 확장 (35개 키) | ✅ |
| 2 | CDPQuestion dataclass + API 엔드포인트 3개 추가 | ✅ |
| 3 | PDF Parser 한글화 기능 삭제 | ✅ |
| 4 | 서버 영구화 (watchdog + Task Scheduler + 방화벽) | ✅ |
| 5 | IP 유연화 (고정IP 스크립트 + hostname 접속) | ✅ |
| 6 | /health 엔드포인트 server 필드 추가 | ✅ |
| 7 | Phase 1 / Phase 2 문서화 (docs/*.md) | ✅ |
| 8 | Hooks 설정 (.claude/settings.local.json) | ✅ |

---

## 2. 서버 영구화 — 핵심 구조

```
[Windows 로그인]
      │
      ▼
Task Scheduler "CDP-Server"
  → pythonw.exe server_watchdog.py
        │
        ▼
   uvicorn (port 8000)
   크래시 시 자동 재시작 (5초 대기)
```

### 관련 파일
- `server_watchdog.py` — uvicorn 감시 + 자동재시작
- `run_as_admin.bat` — 관리자 1회 실행: 방화벽 + Task Scheduler 등록
- `set_static_ip.ps1` — 근무지 복귀 시 고정 IP (10.60.25.146) 설정
- `set_dhcp_ip.ps1` — 외부 이동 시 DHCP 자동 IP 복원

### 접속 방법
| 환경 | URL |
|---|---|
| 로컬 | http://localhost:8000 |
| 사내 고정 IP | http://10.60.25.146:8000 |
| 어디서나 (권장) | http://HY005-327:8000 |
| 외부 | VPN 연결 후 위 주소 사용 |

### 서버 수동 재시작 (문제 발생 시)
```powershell
# 1. 기존 프로세스 종료
taskkill /F /IM python.exe
taskkill /F /IM pythonw.exe

# 2. watchdog 재시작
cd C:\Project\CDP-AI-Platform
start pythonw.exe server_watchdog.py
```

### 자주 발생하는 오류 패턴
| 오류 | 원인 | 해결 |
|---|---|---|
| ERR_CONNECTION_REFUSED | 프로세스 종료됨 | Task Scheduler에서 재시작 or 수동 재시작 |
| ERR_CONNECTION_TIMED_OUT | 방화벽 차단 | run_as_admin.bat 재실행 (CDP-8000 규칙 추가) |
| WinError 10048 | 포트 중복 (두 프로세스 동시 실행) | python.exe + pythonw.exe 모두 종료 후 1개만 시작 |
| VPN 연결 후에도 접속 불가 | IP 변경됨 (DHCP) | set_static_ip.ps1 실행 or hostname으로 접속 |

---

## 3. PDF Parser 한글화 기능 삭제 (Phase 1)

`backend/agents/pdf_parser_agent.py`에서 제거된 항목:
- 한글 번역 관련 AI 호출 로직
- `translate_to_korean()` 관련 함수
- Excel 출력 시 한글 컬럼 생성 부분

**이유:** 실무에서 불필요, 토큰 비용 절감, 코드 복잡도 감소

현재 출력 규칙:
- 시트 1개: `문항_원본` (영문 원본 그대로 출력)
- 출력 폴더: `C:/Project/CDP-AI-Platform/data/outputs/`

---

## 4. Phase 2 추가 API 엔드포인트

`backend/api/routes.py`에 추가된 엔드포인트:

```
POST /api/v1/cdp-answer/questions       # 전체 문항 목록 + 통계 반환
POST /api/v1/cdp-answer/generate-single # 단일 문항 AI 초안 생성
POST /api/v1/cdp-answer/save-answer     # BX(1st_Ans) 또는 CB(Final_Ans) 저장
```

COL_MAP 키 추가 내역 (기존 대비 확장):
- `sub_q_no` (BS, 70), `sub_q_desc` (BT, 71), `sub_q_desc_kr` (BU, 72)
- `sub_q_options` (BV, 73), `current_answer` (BX, 75), `prev_answer` (BZ, 77)
- `final_answer` (CB, 79), `cold_eye` (CC, 80)

---

## 5. Hooks 설정 내용 (.claude/settings.local.json)

세션 시작 시 자동 로드 → **다음 세션부터 적용**

### Hook 1 — Python 문법 검사 (PostToolUse)
- **트리거:** `.py` 파일 Edit/Write 후
- **동작:** `ast.parse()` 로 즉시 문법 검사
- **출력:** `Syntax OK: <파일명>` or 오류 메시지

### Hook 2 — 서버 자동 재시작 (PostToolUse, async)
- **트리거:** `routes.py` Edit/Write 후
- **동작:** python/pythonw 종료 → `server_watchdog.py` 재시작
- **비동기:** 대화 흐름을 막지 않음

### Hook 3 — CLAUDE.md 업데이트 리마인더 (Stop)
- **트리거:** Claude 세션 종료 시
- **동작:** `[CHECK] CLAUDE.md / docs/*.md 업데이트 필요 여부 확인` 메시지 표시

---

## 6. 오류 검증 이력 (이번 세션 중 해결된 주요 오류)

### 6-1. 한글 파일명 bat 실행 오류
- **파일:** `[관리자실행]완전설치.bat`
- **오류:** `]` `[` 가 cmd 특수문자로 해석됨 → parse error
- **해결:** `run_as_admin.bat` 으로 ASCII 이름 변경

### 6-2. VBS→PS1→Python 3단계 체인 충돌 (WinError 10048)
- **원인:** 두 경로(Task Scheduler + VBS)가 동시에 uvicorn 시작 시도
- **해결:** VBS/PS1 체인 전체 폐기 → `pythonw.exe server_watchdog.py` 단일 경로로 통일
- **교훈:** 서버 시작은 **반드시 단일 경로**만 사용

### 6-3. /health 응답에 `server` 필드 없음
- **원인:** 캐시된 구버전 pythonw.exe 프로세스가 응답
- **해결 순서:** `taskkill /F /IM pythonw.exe` → `__pycache__` 삭제 → 재시작
- **교훈:** 코드 변경 후 pythonw.exe 포함 **모든 python 프로세스** 종료 필수

### 6-4. 외부 이동 후 IP 변경으로 접속 불가
- **원인:** DHCP가 10.60.25.146 → 10.60.29.173 으로 변경
- **해결:** `http://HY005-327:8000` (hostname) 사용 + static IP 스크립트 제공
- **교훈:** IP 대신 hostname으로 접속하는 것이 안전

---

## 7. 현재 프로젝트 상태

```
Phase 1 (PDF Parser)     ✅ COMPLETE
Phase 2 (CDP Workbench)  ✅ COMPLETE
Phase 3 (RAG + Scoring)  📋 PLANNED
```

### Phase 3 구현 예정 내용
- RAG 기반 답변 품질 검증
- Scoring Summary 기반 등급 예측
- 지식베이스: `questionnaire_modules.pdf` / `scoring_methodology.pdf` 업로드

---

## 8. Clear 후 Phase 1 개발 재개 방법

새 세션에서 Claude에게 전달할 컨텍스트:

```
CDP AI Platform 개발 중입니다.
- CLAUDE.md 확인 (프로젝트 구조 + Dev Rules)
- docs/phase1_pdf_parser.md (Phase 1 상세)
- docs/phase2_cdp_workbench.md (Phase 2 상세)
- docs/session_log_phase2_server_hooks.md (이번 세션 이력)

Phase 1 수정 작업: backend/agents/pdf_parser_agent.py
```

이렇게 하면 Claude가 전체 맥락을 즉시 복원합니다.
