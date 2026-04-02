# Phase 2 — CDP 답변 자동화 + 워크벤치

> 상태: ✅ 구현 완료 (Phase 1 규칙 기반 + Phase 2 AI 초안)
> 핵심 파일:
> - `backend/agents/cdp_auto_answer_module.py`
> - `backend/core/cdp_prompt_templates.py`
> - `backend/api/routes.py` (CDP 엔드포인트 섹션)
> - `frontend/index.html` (CDP 워크벤치 UI)

---

## 1. 전체 구조

```
cdp_master.xlsx (Comm. Tool_SKEP 시트)
        │
        ▼
ExcelDataLoader.load()   ← 1389개 문항 파싱
        │
        ▼
AnswerTypeClassifier     ← 답변 유형 분류 (단일선택/복수/텍스트/수치 등)
        │
   ┌────┴────┐
   ▼         ▼
Phase 1    Phase 2
규칙기반    AI 초안
(무료)     (API 비용)
   │         │
   └────┬────┘
        ▼
   BX 열 저장 (2025 CDP 1st_Ans.)
```

---

## 2. Excel 열 매핑 (COL_MAP, 0-based)

| 키 | 열 | 인덱스 | 설명 |
|---|---|---|---|
| `order` | A | 0 | 순번 |
| `q_no` | B | 1 | 질문 번호 |
| `main_question_kr` | T | 19 | 한국어 메인 질문 |
| `main_question` | U | 20 | 영어 메인 질문 |
| `scoring_dc` | W | 22 | D등급 채점기준 |
| `scoring_ac` | Y | 24 | A등급 채점기준 |
| `scoring_mc` | AA | 26 | M등급 채점기준 |
| `scoring_lc` | AC | 28 | L등급 채점기준 |
| `d_den_cdp` ~ `l_num_cdp` | AF~AM | 31~38 | CDP 공식 채점 분모/분자 |
| `dependencies` | BG | 58 | 질문 간 의존성 |
| `change_status` | BI | 60 | 전년 대비 변경사항 |
| `rationale` | BK | 62 | Rationale |
| `ambition` | BM | 64 | Ambition |
| `response_options` | BO | 66 | Response options |
| `open_close` | BQ | 68 | O=답변필요 / X=스킵 |
| `sub_q_no` | BS | 70 | 서브 질문 번호 |
| `sub_q_desc` | BT | 71 | 서브 질문 영문 |
| `sub_q_desc_kr` | BU | 72 | 서브 질문 한글 |
| `sub_q_options` | BV | 73 | 선택지 / 형식 |
| `current_answer` | BX | 75 | **2025 1st_Ans. (저장 대상)** |
| `prev_answer` | BZ | 77 | 2024 전년도 답변 |
| `final_answer` | CB | 79 | 2025 Final_Ans. |
| `cold_eye` | CC | 80 | Cold-Eye 검토 |

---

## 3. Phase 1 규칙 기반 (무료)

| 조건 | 처리 |
|---|---|
| `open_close == "X"` | 공백 반환 (Skip) |
| `q_no in FIXED_ANSWERS` | 고정값 반환 (예: [1.1]=English) |
| 전년도 답변 있음 + 변경 없음 + 선택/수치형 | 전년도 그대로 복사 |

**처리율: 전체 1389개 중 약 73%**

---

## 4. Phase 2 AI 초안 (Claude API)

### 할루시네이션 방지 원칙
1. **BV 선택지만** 사용 — 외부 항목 추가 불가
2. **W~AD 채점기준** 프롬프트 주입 → L등급 유도
3. **BZ 전년도 답변** 참조로 일관성 유지
4. 불확실한 수치 → `[VERIFY_REQUIRED]` 태그

### 답변 유형별 AI 출력
| 유형 | 출력 방식 |
|---|---|
| `single_select` | 채점기준 최고 등급 항목 1개 |
| `multi_select` | 해당 항목 전부 (• 구분) |
| `text_short` | 1500자 이내 구체적 답변 |
| `text_long` | 25000자 이내 TCFD/SBTi 참조 서술 |
| `numerical` | 숫자만 (불확실 → VERIFY 태그) |
| `percentage` | 0~100 숫자 |
| `grouped_option` | 그룹별 ☑ 선택 |

---

## 5. API 엔드포인트

```
GET  /api/v1/cdp-answer/excel-list       # Excel 파일 목록
POST /api/v1/cdp-answer/verify-columns   # COL_MAP 검증
POST /api/v1/cdp-answer/run             # 일괄 자동생성 (Phase1 or 1+2)
POST /api/v1/cdp-answer/upload-excel    # Excel 업로드
POST /api/v1/cdp-answer/questions       # 전체 문항 목록 + 통계
POST /api/v1/cdp-answer/generate-single # 단일 문항 AI 초안
POST /api/v1/cdp-answer/save-answer     # BX 또는 CB 열 저장
```

---

## 6. CDP 워크벤치 UI

**접근:** 대시보드 → "CDP 답변 워크벤치" 버튼

### 탭 구성
| 탭 | 기능 |
|---|---|
| 질문 목록 | Q_No 검색, 유형/상태 필터, 300개 테이블 |
| 답변 워크숍 | 문항 상세 + AI 초안 생성 + 편집 + BX/CB 저장 |

### 워크숍 화면
- **왼쪽**: 메인질문(한/영) + 서브질문 + 선택지(BV) + 채점기준(D/A/M/L)
- **오른쪽**: AI 초안 생성 → 텍스트박스 편집 → Excel 저장
- **하단 참조**: 전년도 답변(BZ) 동시 표시

---

## 7. 실측 통계 (cdp_master.xlsx 기준)

| 항목 | 수치 |
|---|---|
| 전체 문항 | 1,389개 |
| Open 문항 | 813개 |
| BX 기입 완료 | 693개 |
| 채점 대상 | 122개 |
| Phase 1 자동처리율 | 73.6% |
| Phase 1+2 처리율 | 98.6% |

---

## 8. Phase 3 계획 (미구현)

- RAG 기반 답변 품질 검증
- Scoring Summary 기반 등급 예측
- questionnaire_modules.pdf / scoring_methodology.pdf KB 업로드
