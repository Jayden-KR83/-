# Claude Code Prompt Log

> 이 파일은 Claude Code 세션에서 사용된 주요 프롬프트를 기록합니다.
> 세션 종료 후에도 작업 맥락을 복구할 수 있도록 유지합니다.

---

## 2026-04-02

### Session 1 (이전 세션 - 복구 불가)
- PDF 파싱 Agent 기능 추가 관련 프롬프트 (세션 종료로 내용 유실)

### Session 2
1. **Prompt:** "내가 10분전에 파싱 기능 추가를 위해 질문한 내용들은 다 사라졌을까? 그리고 현재 CDP-AI-PLATFORM 기능개발은 계속 하면 되는 걸까? 만약에 앞으로도 내가 클로드 코드 이용시 내 개인 계정을 회사 PC에서 사용하는 경우 보안 ISSUE가 있으니 반드시 PROMPT 시행 전에 경고 메시지 알려줘. 내 개인 계정은 rising.yu@gmail.com 이야. 꼭 기억해둬."

2. **Prompt:** "그럼 아까 PDF 파싱 Agent 기능 추가 관련해서 prompt 한 텍스트 다시 불러와줘. 실행은 바로 하지 말고"

3. **Prompt:** "그럼 이런 일이 발생하지 않도록 github에 클로드 코드로 prompt 하는 내용들 모두 기록해줘."

4. **Prompt:** "커밋 부탁해"

5. **Prompt:** "이봐, 지금 개인 계정이 아니라 회사 계정으로 사용중인거 아냐? dennis.kim@sk.com"

6. **Prompt:** "커밋 진행해줘"

7. **Prompt:** "다른 변경 파일들 커밋 부탁해."

8. **Prompt:** "커밋 완료 정확한 의미와 vs code 종료 후 다시 prompt history를 알 수 있다는 의미이지?"

9. **Prompt:** "git push 해줘" → 원격 저장소 URL 설정 (Jayden-KR83/-) 후 push 완료

10. **Prompt:** "새로운 파싱 기능 추가 할거야. 그 전에 prompt 대화내용 clear 해줘."

---

## 2026-04-03

### Session 3
_(Multi-Type PDF Parser & UX Enhancement)_

**Prompt**: Multi-Type PDF Parser & UX Enhancement
- classify_pdf_type(): 첫 5페이지 키워드 분석으로 문서 유형 자동 분류
- Type A (Question Guide): "Reporting Guidance", "Questionnaire" 키워드
- Type B (Scoring Methodology): "Scoring Methodology", "Point Allocation" 키워드
- run_scoring_parser(): Type B 전용 파서 (등급기준/배점 추출)
- run_pdf_parser()에 pdf_type 파라미터 추가 (워크플로우 분기)
- POST /api/v1/classify-pdf 엔드포인트 추가
- Frontend: 문서 유형 확인 패널 (Select Box + 신뢰도 표시 + 모호 시 사용자 선택 유도)

**Files Modified**:
- backend/agents/pdf_parser_agent.py (classify_pdf_type, run_scoring_parser, _build_scoring_rows 등 추가)
- backend/api/routes.py (/classify-pdf 엔드포인트, /parse-pdf에 pdf_type 파라미터)
- frontend/index.html (docTypePanel, confirmDocType() 함수)

### Session 4
_(Scoring Parser 정밀화 — 실제 CDP PDF 스크린샷 기반)_

**Prompt**: 스크린샷 기반 Scoring Methodology 파서 정밀 개선
- **Bug Fix**: run_pdf_parser()에서 pdf_type=None일 때 classify_pdf_type() 자동 호출 누락 수정
- **키워드 추가**: "scoring criteria"를 Type B 분류 키워드에 추가
- **_build_scoring_rows() 전면 재작성**: 실제 CDP Scoring Criteria 구조 반영
  - 섹션 헤더: "1.5 - Scoring criteria" 패턴
  - 질문 참조: "(1.5) - Provide details..." 패턴
  - D/A/M/L 등급기준: "Disclosure/Awareness/Management/Leadership criteria" 헤더
  - Route A/B 분기 파싱
  - Point Allocation 테이블: 빨간 헤더 numerator/denominator 8컬럼 구조
  - "Not scored." 처리, 페이지 헤더/푸터 노이즈 필터링
- **_save_scoring_excel() 개선**: 19컬럼 구조 (D_num~L_den 포함), 행 유형별 색상 스타일링
- **패턴 검증**: SCORING_HEADER, CRITERIA_HEADER, POINTS_MAX, ROUTE, Point Allocation 모두 테스트 통과

**Files Modified**:
- backend/agents/pdf_parser_agent.py (패턴 재정의 + _build_scoring_rows 재작성 + auto-classification 수정)

### Session 5
_(Scoring Parser 전면 재설계 — 문항 단위 그룹핑)_

**문제**: scoring method 파싱이 questionnaire와 동일하게 flat row로 출력, 다른 파일도 다운로드 표시
**원인 분석**:
1. `_build_scoring_rows()` 가 라인 단위 flat 출력 → questionnaire 출력과 구분 불가
2. `confirmDocType()` 에서 `viewOutputs()` 호출 → output 폴더 전체 파일 표시
3. 최대배점(2/2)이 Disclosure 섹션 내에서 나타나 전체 배점으로 인식 안 됨

**수정 내용**:
- `_build_scoring_questions()` 전면 재설계: **문항 1개 = Excel 1행** (D/A/M/L 기준이 컬럼)
  - 22컬럼: 문항ID, 질문내용, 페이지, 최대배점, D/A/M/L 기준+배점, D/A/M/L num/den, 테마, 섹터
  - Route A/B → `[ROUTE A] ...` `[OR]` `[ROUTE B] ...` 형태로 Management 기준에 통합
  - Theme/Sector 테이블: 헤더 행 스킵, 데이터 행만 추출
  - "for this question" 최대배점 인식: Disclosure 섹션 내에서도 전체 배점으로 설정
- `_save_scoring_excel()` 재작성: 시트명 "채점_방법론", 녹색/흰색 교대 행 스타일, 자동 열 너비
- Frontend `confirmDocType()`: `viewOutputs()` 제거 → 현재 파일 다운로드만 표시
- `backend/tests/test_scoring_parser.py` 테스트 5건 작성 및 전체 통과

**Files Modified**:
- backend/agents/pdf_parser_agent.py (_build_scoring_questions 재설계 + _save_scoring_excel 재작성)
- frontend/index.html (viewOutputs 제거)
- backend/tests/test_scoring_parser.py (신규)

### Session 6
_(Scoring Parser 라우팅 완전 실패 수정)_

**문제**: scoring PDF 업로드해도 questionnaire 파싱 결과(행_유형/질문번호 컬럼)가 나옴
**근본 원인**: 3가지
1. FastAPI `pdf_type` 파라미터가 `Query` 어노테이션 없이 `File(...)`과 함께 사용 → query param 미인식 가능성
2. 파일명 기반 감지 로직 없음 → "scoring_methodology" 파일명이어도 Type A로 파싱
3. auto-classification이 content keyword만 사용 → 실제 CDP 문서에서 "Questionnaire" 키워드도 포함되어 있으면 ambiguous

**수정 (3중 방어)**:
1. `routes.py`: `Query(None)` 명시적 어노테이션 + 파일명에 "scoring" 포함 시 강제 TYPE_B
2. `run_pdf_parser()`: 파일명 기반 감지(최우선) → 명시적 pdf_type → 자동분류 (3단계)
3. `classify_pdf_type()`: 파일명에 "scoring" 포함 시 confidence=1.0으로 즉시 TYPE_B 반환
4. 전체 흐름에 로깅 추가 (routes + pdf_parser_agent)

**Files Modified**:
- backend/api/routes.py (Query 어노테이션, 파일명 감지, 로깅)
- backend/agents/pdf_parser_agent.py (3단계 분류 로직, 파일명 감지)

### Session 7
_(업로드 2-Zone 분리 + 파일명 키워드 절대 원칙)_

**요구**: 업로드 구역 2개로 분리, 파일명 기반 파서 결정, CDP 8개 파일 지식 저장
**수정**:
- Frontend: 모달을 2-Zone 그리드로 재설계
  - 왼쪽(녹색): 문항 및 응답 조건 (Questionnaire_Module) — 여러 파일 가능
  - 오른쪽(분홍): 채점 방법론 D/A/M/L (Scoring_Methodology) — 단일 파일
  - 각 Zone별 독립 업로드 버튼, pdf_type 명시적 전달
  - 기존 classify-pdf / confirmDocType 흐름 완전 제거
- Backend: `_detect_pdf_type_by_filename()` 도입
  - questionnaire_module → TYPE_A, scoring_methodology/scoring → TYPE_B
  - /classify-pdf 엔드포인트 제거
- Memory: CDP 8개 PDF 파일 구조 + Group A/B 분류 + 파싱 절대 원칙 저장

**테스트 결과**: 5개 전체 통과
1. 파일명 라우팅 (8개 실제 파일명 + fallback) PASS
2. Backend 라우팅 로직 PASS
3. API routes 검증 PASS
4. Frontend 2-Zone HTML 구조 + 기존 코드 제거 PASS
5. Scoring parser 전체 (패턴/빌드/Excel/다중문항/배점표) PASS

### Session 8
_(근본 원인 발견: 업로드 파일 손상 33bytes + AgentResult.error 속성 오류)_

**근본 원인**: uploads 폴더의 scoring PDF가 **33 bytes로 손상** (원본 4MB). 이전 classify-pdf 호출 시 File 스트림이 소비된 상태에서 다시 저장하면서 빈 파일이 됨. → pdfplumber "No /Root object" 에러 → scoring parser 실패 → questionnaire parser가 fallback으로 실행됨

**수정**:
1. `routes.py`: `file.file.seek(0)` 추가 — File 스트림 위치 초기화 후 저장
2. `routes.py`: 저장 후 파일 크기 검증 (< 100 bytes → knowledge에서 복구)
3. `routes.py`: `/parse-pdf/multi` — `result.error` → `result.error_message` 수정
4. `pdf_parser_agent.py`: 파일명 "scoring" 체크를 `if pdf_type is None` 조건 밖으로 이동 (무조건 실행)
5. `pdf_parser_agent.py`: `_build_scoring_questions` — 실제 PDF 순서 반영 (질문참조가 섹션헤더보다 먼저)
6. `pdf_parser_agent.py`: `_detect_point_allocation_table` — 실제 PDF의 2행 헤더 + 빈 셀 구조 처리
7. `pdf_parser_agent.py`: Theme 테이블 — 빈 셀/중복값 처리
8. uploads 폴더의 손상된 파일을 knowledge에서 복구

**실제 PDF 테스트 결과**: pages 9-15 → 8개 문항, 시트 "채점_방법론", _scoring.xlsx 정상 생성
