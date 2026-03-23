# PDF Extraction Skill

## 역할
CDP 가이드 PDF에서 텍스트, 비정형 표, 문항 데이터를 추출하고 정제한다.
Claude API를 활용해 비정형 데이터의 의미를 해석하고 구조화한다.

## 핵심 전략: 2-Pass + AI 보정
### Pass 1: pdfplumber (텍스트 + 단순 표)
- 일반 텍스트, 단순 구조 표에 우선 사용
### Pass 2: camelot (복잡한 표)
- lattice 모드: 선이 있는 표
- stream 모드: 선 없는 공백 구분 표
### Pass 3: Claude API 보정 (Pass 1/2 품질 미달 시)
- 추출된 텍스트를 Claude에게 전달해 구조화 요청
- 비정형 표, 잘못 파싱된 문항 ID 복구

## 데이터 정제 규칙
1. None, '', 'nan' 셀은 빈 문자열로 통일
2. 줄바꿈(\n) 포함 셀은 공백으로 대체
3. 헤더가 None인 경우 col_0, col_1... 자동 부여
4. 완전히 빈 행/열 제거

## 문항 인식 패턴
- 패턴 A: "C1.1", "W2.3a" 등 영숫자 코드로 시작
- 패턴 B: Points/점수 정보 포함 행
- 패턴 C: 대문자로 시작하는 섹션 제목 다음 행
- 패턴 D (AI 보정): 위 패턴 실패 시 Claude API로 문항 경계 판단

## Excel 출력 스키마
| 컬럼 | 설명 |
|------|------|
| question_id | 문항 코드 (예: C1.1) |
| question_text | 문항 내용 |
| guidance | 작성 가이드 |
| max_points | 최대 점수 |
| page_num | PDF 페이지 번호 |

## 품질 기준
- question_id 인식률 > 90%
- 표 셀 누락률 < 5%
