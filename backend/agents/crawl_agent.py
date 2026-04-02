"""
Crawl Agent (Phase 1)
skills/crawling_guide.skill.md 의 지침을 따른다.
ESG/CDP 관련 외부 정보를 수집하고 Claude API로 분석한다.
"""
import time
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

from backend.core.models import AgentResult, AgentStatus, ValidationResult, CrawlResult
from backend.core.crawler import WebCrawler, PlaywrightCrawler
from backend.core.skill_loader import load_skill
from backend.core.llm_client import get_claude_client


# 사전 검토된 크롤링 허용 사이트 목록 (crawling_guide.skill.md 기준)
ALLOWED_DOMAINS = {
    # ── CDP / ESG 국제 기관 (기존 유지) ─────────────────────
    "cdp.net",
    "ghgprotocol.org",
    "sciencebasedtargets.org",
    "science-basedtargets.org",  # 레거시 도메인도 허용
    "iea.org",
    # ── ESG 기준·공시 국제 기관 (공개) ──────────────────────
    "unglobalcompact.org",       # UN 글로벌 컴팩트
    "globalreporting.org",       # GRI 표준
    "kcgs.or.kr",                # 한국ESG기준원
    "isealalliance.org",         # ISEAL Alliance (지속가능 표준)
    "sustainablefinance.hsbc.com", # HSBC 지속가능금융 (공개 리포트)
    # ── 건설·녹색건물·탄소중립 (공개) ──────────────────────
    "worldgbc.org",              # World Green Building Council
    "unepfi.org",                # UNEP Finance Initiative (건물 섹터)
    "buildingsandcities.org",    # Buildings and Cities 연구 저널
    "cak.or.kr",                 # 대한건설협회
    "kca.or.kr",                 # 한국건설산업연구원
}


# 카테고리별 크롤링 URL 프리셋
CRAWL_PRESETS = {
    # ── 기존 유지 ────────────────────────────────────────────
    "cdp_esg": {
        "label": "CDP/ESG 국제 기관",
        "query": "CDP ESG 2024 채점 기준 환경공시 변경사항",
        "summary_focus": "cdp",
        "urls": [
            "https://cdp.net/en/guidance",
            "https://ghgprotocol.org/standards",
            "https://sciencebasedtargets.org/resources",
            "https://iea.org/topics/clean-energy-transitions",
        ],
    },
    # ── ESG 기준·공시 최신 동향 (접근 가능 공개 기관) ────────
    "rating_agencies": {
        "label": "ESG 기준·공시 최신 동향",
        "query": "ESG 공시 기준 최신 동향 ISSB CSRD GRI 지속가능성 환경 사회 지배구조 2024 2025",
        "summary_focus": "esg_standards",
        "urls": [
            "https://www.globalreporting.org/about-gri/mission-history/",
            "https://www.unglobalcompact.org/what-is-gc/our-work/environment",
            "https://www.kcgs.or.kr",
            "https://iea.org/topics/tracking-clean-energy-progress",
            "https://ghgprotocol.org/standards",
        ],
    },
    # ── 건설·녹색건물 ESG 최신 동향 (공개 국제 기관) ─────────
    "construction_esg": {
        "label": "건설·녹색건물 ESG 최신 동향",
        "query": "건설 녹색건물 탄소중립 Net-Zero ESG 최신 동향 2024 2025 환경경영 그린빌딩 Scope3",
        "summary_focus": "construction_esg",
        "urls": [
            "https://www.worldgbc.org/advancing-net-zero",
            "https://www.worldgbc.org/news-media",
            "https://www.unepfi.org/buildings/",
            "https://ghgprotocol.org/standards",
            "https://iea.org/topics/buildings",
        ],
    },
}


def _is_allowed_url(url: str) -> bool:
    """허용된 도메인인지 확인"""
    from urllib.parse import urlparse
    domain = urlparse(url).netloc.lower()
    return any(allowed in domain for allowed in ALLOWED_DOMAINS)


_SUMMARY_PROMPTS = {
    "cdp": (
        "위 내용에서 CDP 업무에 관련된 핵심 정보를 한국어로 요약해주세요.\n"
        "특히 채점 기준 변경사항, 데이터 요구사항, 업종별 벤치마크 관련 내용에 집중하세요.\n"
        "없는 정보는 억지로 만들지 말고 수집된 내용 범위 내에서 답변하세요."
    ),
    "esg_standards": (
        "위 내용에서 ESG 공시·기준과 관련된 최신 동향을 한국어로 요약해주세요.\n"
        "다음 항목을 중심으로 정리하세요:\n"
        "1) 새로운 ESG 공시 기준 또는 규제 변화 (ISSB, CSRD, GRI 등)\n"
        "2) 주요 ESG 평가 방법론 업데이트\n"
        "3) 환경(E)·사회(S)·지배구조(G) 측면의 중요 이슈\n"
        "4) 국내외 기업 대응 동향\n"
        "수집된 내용을 바탕으로 실무에 유용한 인사이트를 제공하세요."
    ),
    "construction_esg": (
        "위 내용에서 건설·건물·부동산 분야 ESG 최신 동향을 한국어로 요약해주세요.\n"
        "다음 항목을 중심으로 정리하세요:\n"
        "1) 녹색건물(Net-Zero, Green Building) 관련 최신 기준·인증\n"
        "2) 건설 분야 탄소중립 목표 및 Scope 3 배출 감축 동향\n"
        "3) 건설업계에 적용되는 ESG 규제·공시 요구사항\n"
        "4) 주목할 만한 사례 또는 기술 트렌드\n"
        "건설 기업의 ESG 전략 수립에 실질적으로 활용할 수 있는 내용으로 정리하세요."
    ),
}


def _summarize_with_claude(
    content: str,
    query: str,
    skill_content: str,
    summary_focus: str = "cdp",
) -> str:
    """수집된 웹 컨텐츠를 Claude API로 요약/분석 (카테고리별 프롬프트)"""
    try:
        client = get_claude_client()
        focus_instruction = _SUMMARY_PROMPTS.get(summary_focus, _SUMMARY_PROMPTS["cdp"])
        prompt = (
            f"다음은 ESG 관련 웹페이지에서 수집한 내용입니다.\n"
            f"수집 목적: {query}\n\n"
            f"웹 컨텐츠:\n{content[:5000]}\n\n"
            f"{focus_instruction}"
        )
        return client.chat(prompt, system_prompt=skill_content, temperature=0.2)
    except Exception as e:
        logger.warning(f"Claude 요약 실패: {e}")
        return content[:1000]


def _validate_crawl_results(results: List[CrawlResult]) -> ValidationResult:
    success_count = sum(1 for r in results if r.success)
    total = len(results)
    score = success_count / max(total, 1)
    warnings = []
    errors = []
    failed = [r.url for r in results if not r.success]
    if failed:
        warnings.append(f"수집 실패 URL {len(failed)}개: {failed[:3]}")
    empty_content = [r.url for r in results if r.success and len(r.content) < 100]
    if empty_content:
        warnings.append(f"내용 없는 페이지: {len(empty_content)}개")
        score -= 0.1 * len(empty_content)
    score = max(0.0, min(1.0, score))
    return ValidationResult(
        is_valid=score > 0,
        confidence_score=round(score, 2),
        warnings=warnings,
        errors=errors,
        needs_human_review=score < 0.5,
    )


def run_crawl_agent(
    urls: List[str],
    query: str = "CDP ESG 정보",
    use_playwright: bool = False,
    summarize: bool = True,
    category: Optional[str] = None,
) -> AgentResult:
    """
    Crawl Agent 메인 실행.

    Args:
        urls: 수집할 URL 목록
        query: 수집 목적/검색 쿼리 (Claude 요약 시 활용)
        use_playwright: JS 렌더링 필요 시 True
        summarize: Claude API로 요약 여부

    Returns:
        AgentResult (data: {"results": [...], "summary": "..."})
    """
    start = time.time()
    agent_name = "CrawlAgent"

    # 카테고리 프리셋 적용
    if category and category in CRAWL_PRESETS:
        preset = CRAWL_PRESETS[category]
        urls = preset["urls"]
        if not query or query == "CDP ESG 정보":
            query = preset["query"]
        logger.info(f"[{agent_name}] 카테고리 프리셋 적용: {category} ({len(urls)}개 URL)")

    # SKILL.md 로드
    try:
        skill_content = load_skill("crawling_guide")
        logger.info(f"[{agent_name}] SKILL.md 로드 완료")
    except FileNotFoundError:
        skill_content = ""

    # PDF/바이너리 URL 사전 필터링 (HTML 크롤러로 처리 불가)
    pdf_skipped = []
    html_urls = []
    for url in urls:
        lower = url.lower().split("?")[0]
        if lower.endswith((".pdf", ".docx", ".xlsx", ".zip", ".pptx")):
            pdf_skipped.append(url)
            logger.info(f"[{agent_name}] 바이너리 파일 건너뜀 (HTML 크롤러 미지원): {url}")
        else:
            html_urls.append(url)
    urls = html_urls

    # 허용 도메인 필터링
    filtered_urls = []
    blocked = []
    for url in urls:
        if _is_allowed_url(url):
            filtered_urls.append(url)
        else:
            blocked.append(url)
            logger.warning(f"[{agent_name}] 허용되지 않은 도메인: {url}")

    if blocked:
        logger.warning(
            f"[{agent_name}] {len(blocked)}개 URL 차단됨 (crawling_guide.skill.md 미허용 도메인). "
            f"허용 대상: {ALLOWED_DOMAINS}"
        )

    if not filtered_urls:
        return AgentResult(
            agent_name=agent_name,
            status=AgentStatus.FAILED,
            error_message=f"허용된 URL 없음. 크롤링 허용 도메인: {ALLOWED_DOMAINS}",
        )

    # 크롤링 실행
    if use_playwright:
        crawler = PlaywrightCrawler()
        results = [crawler.fetch(url) for url in filtered_urls]
    else:
        crawler = WebCrawler()
        results = crawler.fetch_multiple(filtered_urls)

    validation = _validate_crawl_results(results)

    # Claude API로 요약 (카테고리별 프롬프트 적용)
    summary_focus = CRAWL_PRESETS.get(category or "", {}).get("summary_focus", "cdp")
    combined_summary = ""
    if summarize and any(r.success for r in results):
        combined_text = "\n\n".join(
            f"[출처: {r.url}]\n{r.content[:2000]}"
            for r in results if r.success
        )
        combined_summary = _summarize_with_claude(
            combined_text, query, skill_content, summary_focus=summary_focus
        )

    data = {
        "query": query,
        "category": category,
        "total_urls": len(filtered_urls) + len(blocked) + len(pdf_skipped),
        "crawled": len(filtered_urls),
        "blocked_urls": blocked,
        "pdf_skipped": pdf_skipped,
        "results": [r.model_dump() for r in results],
        "summary": combined_summary,
    }

    status = AgentStatus.SUCCESS if validation.is_valid else AgentStatus.NEEDS_REVIEW
    return AgentResult(
        agent_name=agent_name,
        status=status,
        data=data,
        validation=validation,
        processing_time_sec=round(time.time() - start, 2),
        created_at=time.strftime("%Y-%m-%d %H:%M:%S"),
    )

