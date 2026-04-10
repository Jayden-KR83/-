# Incident Report: Scoring Methodology PDF Parser 구현 실패

**작성일**: 2026-04-03
**영향 범위**: CDP PDF Parsing Agent — Scoring Methodology 파싱 기능
**심각도**: Critical (핵심 기능 미동작)
**총 소요 시간**: ~2시간 (Session 3~8, 6회 반복 시도)
**최종 상태**: Session 8에서 근본 원인 발견 및 수정 완료

---

## 1. 요약

Scoring Methodology PDF를 업로드하면 Questionnaire Module 파싱 결과(`_parsed.xlsx`)가 출력되는 문제가 **6개 세션 동안 반복**되었다. 코드 로직은 매 세션마다 수정되었지만, 실제 서비스에서는 동일한 실패가 계속되었다.

근본 원인은 **업로드 파일이 33 bytes로 손상**되어 있었기 때문이다. Session 3에서 도입된 `/classify-pdf` 엔드포인트가 File 스트림을 소비한 후, `/parse-pdf` 에서 같은 스트림을 다시 저장하면서 빈 파일이 생성되었다. 이후 모든 scoring 파싱 시도는 이 손상된 파일을 읽으려다 실패했고, 결과적으로 이전에 생성된 questionnaire 출력 파일만 남아 사용자에게 표시되었다.

---

## 2. 타임라인

| Session | 시도한 수정 | 결과 | 실패 원인 |
|---------|-----------|------|----------|
| **3** | `classify_pdf_type()` 콘텐츠 분석 기반 분류 + `/classify-pdf` 엔드포인트 + `confirmDocType()` UI | 테스트 통과, 실서비스 실패 | **File 스트림 소비 후 재저장 → 파일 손상 (이 시점에 33 bytes 파일 생성)** |
| **4** | 자동분류 누락 수정, "scoring criteria" 키워드 추가, 패턴 재작성 | 단위 테스트 통과, 실서비스 실패 | 손상 파일 지속. 패턴 개선은 유효했으나 파일을 열지 못해 무의미 |
| **5** | `_build_scoring_questions()` 전면 재설계 (문항 1행 구조) | 단위 테스트 통과, 실서비스 실패 | 동일. Excel 구조 개선은 유효했으나 파일 손상 미발견 |
| **6** | FastAPI `Query(None)` 명시, 파일명 기반 감지 3중 방어 | 단위 테스트 통과, 실서비스 실패 | 라우팅 자체는 정상이었으나 손상 파일로 pdfplumber 에러 |
| **7** | 업로드 2-Zone UI 분리, `pdf_type` 명시적 전달, classify 제거 | 단위 테스트 통과, 실서비스 실패 | UI 개선은 유효. 여전히 손상 파일 미발견 |
| **8** | **실제 PDF 파일 크기 확인 → 33 bytes 발견 → 근본 원인 확정** | 실서비스 성공 | `file.file.seek(0)` + 크기 검증 + 파일 복구 |

---

## 3. 근본 원인 분석 (Root Cause)

### 직접 원인
```
data/uploads/...Scoring_Methodology...pdf  →  33 bytes (손상)
data/knowledge/...Scoring_Methodology...pdf → 4,035,714 bytes (원본)
```

### 발생 경로
```
Session 3에서 도입된 2단계 업로드 흐름:

1. 사용자가 PDF 선택 → "추출 시작" 클릭
2. Frontend: selectedFiles[0]을 /classify-pdf로 POST (FormData)
   → 서버: file.file 스트림을 읽어서 분류
   → 서버: shutil.copyfileobj(file.file, f) → 파일 저장 (정상, 4MB)
3. 사용자가 "확인 후 추출" 클릭
4. Frontend: selectedFiles[0]을 /parse-pdf로 POST (FormData)
   → 서버: shutil.copyfileobj(file.file, f) → 파일 저장
   → ⚠️ 이 시점에 File 스트림은 이미 classify에서 소비됨
   → 저장된 파일 = 33 bytes (빈 스트림)
5. pdfplumber.open() → "No /Root object! - Is this really a PDF?"
6. run_scoring_parser() → FAILED 반환
7. 이전에 생성된 _parsed.xlsx만 outputs 폴더에 존재
8. 사용자는 questionnaire 결과만 보게 됨
```

### 왜 단위 테스트에서 발견하지 못했는가

| 테스트 방식 | 한계 |
|------------|------|
| 시뮬레이션 데이터 (text + table dict) | 실제 PDF 파일 I/O를 거치지 않음 |
| `run_scoring_parser()` 직접 호출 | API 레이어의 file.file 스트림 문제를 우회 |
| FastAPI TestClient | 매 요청마다 새 파일 객체를 생성하므로 스트림 소비 문제 미재현 |
| 파일 크기 미확인 | 파일 존재 여부만 체크, 크기/무결성 미검증 |

---

## 4. 부수적 버그 (함께 발견됨)

| 버그 | 위치 | 영향 |
|------|------|------|
| `result.error` → `result.error_message` | `/parse-pdf/multi` endpoint | Questionnaire 3파일 동시 파싱 시 `'AgentResult' has no attribute 'error'` 에러로 전체 실패 |
| 실제 PDF 텍스트 순서 불일치 | `_build_scoring_questions()` | `(1.5)` 질문참조가 `1.5 - Scoring criteria` 헤더보다 **먼저** 출현 → 문항이 2개로 분리되어 데이터 소실 |
| Point Allocation 테이블 구조 불일치 | `_detect_point_allocation_table()` | 실제 PDF 테이블이 빈 셀 다수 + 2행 헤더 구조 → 테이블 인식 실패 |
| Theme 테이블 파싱 오류 | `_build_scoring_questions()` | 실제 PDF에서 `['CC', 'CC', '', '', 'GN/CN/...', '']` 형태 → 빈 셀/중복값 미처리 |

---

## 5. 적용된 수정 사항

### 근본 수정 (파일 손상 방지)
```python
# routes.py /parse-pdf endpoint
file.file.seek(0)  # 스트림 위치 초기화 (핵심 수정)
with open(save_path, "wb") as f:
    shutil.copyfileobj(file.file, f)

# 저장 후 크기 검증
if save_path.stat().st_size < 100:
    # knowledge 폴더에서 원본 자동 복구
    kb_file = knowledge_dir / file.filename
    if kb_file.exists():
        shutil.copy2(str(kb_file), str(save_path))
```

### 구조 수정
- 업로드 UI를 2-Zone으로 분리 (Questionnaire / Scoring 독립)
- `/classify-pdf` 엔드포인트 **제거** (2단계 업로드 흐름 자체를 폐기)
- `pdf_type`을 프론트엔드에서 Zone별로 명시적 전달

### 파일명 기반 파서 결정 (절대 원칙)
- 파일명에 `scoring` 포함 → 무조건 Scoring Parser
- 파일명에 `questionnaire` 포함 → 무조건 Questionnaire Parser
- PDF 내용 기반 자동 분류는 사용하지 않음

---

## 6. 교훈 (Lessons Learned)

### 6-1. 파일 I/O 무결성 검증 필수
> 파일을 저장한 후 반드시 크기/해시를 검증해야 한다. "파일이 존재한다"와 "파일이 정상이다"는 다르다.

### 6-2. 단위 테스트의 한계 인식
> 시뮬레이션 데이터로 패턴 매칭/구조 변환을 테스트하는 것은 유효하지만, **실제 파일 I/O + API 레이어 + 브라우저 업로드** 를 결합한 통합 테스트가 없으면 실서비스 실패를 잡지 못한다.

### 6-3. 증상이 아닌 원인을 추적해야 한다
> "왜 questionnaire 결과가 나오는가?" → Session 3~7에서는 라우팅/패턴/UI를 반복 수정했지만, 실제 원인은 **파일 크기 33 bytes**라는 단순한 사실이었다. 실제 파일을 열어보는 디버깅을 Session 8까지 하지 않았다.

### 6-4. 2단계 업로드 흐름은 위험하다
> `classify` → `parse` 2단계 흐름에서 File 스트림이 1회 소비되면 2번째 요청에서 빈 파일이 생성된다. 이 패턴은 처음부터 피해야 했다.

---

## 7. 파일명 길이 관련

현재 파일명이 길지만 **파싱 로직에는 영향 없음**. 파일명 키워드 매칭은 `filename.lower()`에서 `"scoring"` 또는 `"questionnaire"` 포함 여부만 확인하므로 파일명 길이는 무관하다.

다만 Excel 출력 파일명이 `원본파일명_scoring.xlsx`로 생성되어 매우 길어질 수 있으므로, 가독성을 위해 짧게 줄이는 것은 선택사항이다.

**예시 (짧게 줄이는 경우):**
```
AS-IS: GR A_CDP_Full_Corporate_Scoring_Methodology_2025_-_Climate_change_v1.0(20250430).pdf
TO-BE: CDP_Scoring_Methodology_CC_2025.pdf
```

---

## 8. 현재 상태

| 항목 | 상태 |
|------|------|
| Questionnaire 파싱 (Zone A) | 동작 확인 필요 (AgentResult.error 수정 완료) |
| Scoring 파싱 (Zone B) | **pages 9-15 테스트 성공** (8문항, 채점_방법론 시트, _scoring.xlsx) |
| 전체 797페이지 파싱 | 서버 재시작 후 확인 필요 (~4분 소요 예상) |
| 업로드 파일 손상 방지 | `file.seek(0)` + 크기 검증 + knowledge 복구 적용 |
