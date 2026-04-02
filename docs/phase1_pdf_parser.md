# Phase 1 — PDF Parser Agent

> 상태: ✅ COMPLETE
> 핵심 파일: `backend/agents/pdf_parser_agent.py`

---

## 1. 목적

CDP 가이드 PDF에서 비정형 표·문항 데이터를 추출하여 채점용 Excel로 구조화.

---

## 2. 색상 기반 셀 분류 규칙

| 상수 | 키 이름 | 조건 | 의미 |
|---|---|---|---|
| `CC_TITLE` | `"je-mok"` | avg ≤ 0.80 | 짙은 회색 — 제목 행 |
| `CC_HEADER` | `"he-do"` | avg ≤ 0.96 | 연회색 — 헤더 행 |
| `CC_CONTENT` | `"nae-yong"` | avg > 0.96 | 흰색 — 내용 행 |

---

## 3. 테이블 유형 분류

| 유형 | 조건 | 처리 |
|---|---|---|
| `numbered` | 숫자 헤더 있음 | number/Sub/Options 추출 |
| `tags` | Tags 행 존재 | CDP 3개 카테고리만 추출 |
| `skip` | "Requested content" 또는 "Explanation of terms" 헤더 | 무시 |
| `continuation` | 숫자 헤더 없음 | 이전 행 col_ranges에 options append |

---

## 4. CDP 태그 필터 (3종)

- authority type
- environmental issue
- questionnaire sector

---

## 5. Excel 출력 규칙

- 시트 1개만: `"吏덈Ц_援ъ"` (표준 시트명)
- 출력 폴더: `C:/Project/CDP-AI-Platform/data/outputs/`
- 한글화 기능: **삭제됨** (불필요 판단, 제거 완료)

---

## 6. API 엔드포인트

```
POST /api/v1/parse-pdf
  - file: PDF 업로드
  - page_start / page_end: 페이지 범위 (선택)
```

---

## 7. 주요 의사결정 이력

| 결정 | 이유 |
|---|---|
| 2-Pass 추출 방식 | 비정형 표에서 병합 셀 오탐 방지 |
| Claude AI 보정 | pdfminer 오추출 후처리 |
| 한글화 기능 제거 | 실무에서 불필요, 토큰·복잡도 절감 |

---

## 8. 다음 단계 연계

Phase 1 출력 Excel → Phase 2 CDP 자동채점 Agent 입력값으로 사용
