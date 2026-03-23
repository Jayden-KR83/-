# Crawling Guide Skill

## 역할
ESG/CDP 관련 외부 데이터를 수집하기 위한 크롤링 전략과 대상을 정의한다.

## 크롤링 허용 대상 (사전 검토 완료)
| 사이트 | 수집 데이터 | robots.txt 확인 |
|--------|------------|----------------|
| cdp.net/en/guidance | CDP 공식 가이드 업데이트 | 허용 |
| ghgprotocol.org | GHG 산정 기준 | 허용 |
| science-basedtargets.org | SBT 기준 정보 | 허용 |
| iea.org/reports | 에너지 통계 | 허용 (공개 페이지만) |

## 크롤링 금지 사항
- robots.txt 불허 페이지 크롤링 금지
- 로그인이 필요한 페이지 자격증명 사용 금지
- 1초 이하 간격 연속 요청 금지 (서버 부하 방지)
- 수집 데이터의 저작권 확인 필수

## 기술 전략
- 정적 페이지: httpx + BeautifulSoup4
- 동적 페이지(JS 렌더링): Playwright
- Rate limiting: 요청 간 1~3초 대기
- User-Agent: 명시적 봇 식별자 사용

## 수집 데이터 활용
- CDP 채점 기준 변경사항 모니터링
- 업종별 벤치마크 데이터 수집
- 답변 초안 작성 시 참고 데이터 제공 (Phase 3)
