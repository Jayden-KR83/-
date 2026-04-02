# Crawling Guide Skill

## 역할
ESG/CDP 관련 외부 데이터를 수집하기 위한 크롤링 전략과 대상을 정의한다.

## 크롤링 카테고리 및 허용 대상

### 카테고리 1: CDP/ESG 국제 기관 (기존 유지)
| 사이트 | 수집 목적 | 요약 초점 |
|--------|---------|---------|
| cdp.net/en/guidance | CDP 공식 가이드 업데이트 | 채점 기준, 데이터 요구사항 |
| ghgprotocol.org/standards | GHG 산정 기준 | 배출량 산정 방법론 |
| sciencebasedtargets.org/resources | SBT 기준 정보 | 과학기반 감축 목표 |
| iea.org/topics/clean-energy-transitions | 청정에너지 전환 동향 | 에너지 통계·전망 |

### 카테고리 2: ESG 기준·공시 최신 동향
| 사이트 | 수집 목적 | 요약 초점 |
|--------|---------|---------|
| globalreporting.org | GRI 표준 현황 | ESG 공시 기준 변화 |
| unglobalcompact.org | UN 글로벌 컴팩트 환경 | E·S·G 이슈 동향 |
| kcgs.or.kr | 한국ESG기준원 | 국내 ESG 평가·공시 기준 |
| iea.org/topics/tracking | IEA 청정에너지 트래킹 | 에너지 전환 지표 |
| ghgprotocol.org | GHG 표준 | 배출 기준 업데이트 |

**요약 방향:** ISSB·CSRD·GRI 등 공시 기준 변화, ESG 평가 방법론 업데이트, 국내외 규제 동향

### 카테고리 3: 건설·녹색건물 ESG 최신 동향
| 사이트 | 수집 목적 | 요약 초점 |
|--------|---------|---------|
| worldgbc.org/advancing-net-zero | 세계녹색건물협의회 Net-Zero | 넷제로 건물 기준·사례 |
| worldgbc.org/news-media | 녹색건물 최신 뉴스 | 건설업계 ESG 이슈 |
| unepfi.org/buildings | UNEP FI 건물 섹터 | 건물 금융·ESG 연계 |
| ghgprotocol.org/standards | GHG Protocol Scope 3 | 건설 공급망 배출 |
| iea.org/topics/buildings | IEA 건물 부문 에너지 | 에너지 효율·탄소 |

**요약 방향:** 녹색건물 인증·기준, 건설 Scope 3 감축, 탄소중립 사례, 건설업 ESG 규제

## 크롤링 금지 사항
- robots.txt 불허 페이지 크롤링 금지
- 로그인이 필요한 페이지 자격증명 사용 금지
- 1초 이하 간격 연속 요청 금지
- PDF/바이너리 파일 직접 다운로드 금지 (자동 필터링 적용)
- 저작권 확인 필수

## 기술 전략
- 정적 HTML: urllib.request (표준 라이브러리, timeout 30초)
- 동적 페이지: Playwright (선택적)
- Rate limiting: 요청 간 2초 대기
- PDF/바이너리 URL 자동 필터링 (.pdf, .docx, .xlsx 등)
- DNS 해석 실패 시 해당 URL 건너뜀 (방화벽 차단 대응)
