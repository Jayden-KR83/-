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
    "cdp.net",
    "ghgprotocol.org",
    "science-basedtargets.org",
    "iea.org",
}


def _is_allowed_url(url: str) -> bool:
    """허용된 도메인인지 확인"""
    from urllib.parse import urlparse
    domain = urlparse(url).netloc.lower()
    return any(allowed in domain for allowed in ALLOWED_DOMAINS)


def _summarize_with_claude(content: str, query: str, skill_content: str) -> str:
    """수집된 웹 컨텐츠를 Claude API로 요약/분석"""
    try:
        client = get_claude_client()
        prompt = f"""다음은 ESG/CDP 관련 웹페이지에서 수집한 내용입니다.
검색 목적: {query}

웹 컨텐츠:
{content[:4000]}

위 내용에서 CDP 업무에 관련된 핵심 정보를 한국어로 요약해주세요.
특히 채점 기준, 데이터 요구사항, 업종별 벤치마크 관련 내용에 집중하세요."""

        return client.chat(prompt, system_prompt=skill_content, temperature=0.2)
    except Exception as e:
        logger.warning(f"Claude 요약 실패: {e}")
        return content[:1000]  # 요약 실패 시 원본 일부 반환


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

    # SKILL.md 로드
    try:
        skill_content = load_skill("crawling_guide")
        logger.info(f"[{agent_name}] SKILL.md 로드 완료")
    except FileNotFoundError:
        skill_content = ""

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

    # Claude API로 요약
    combined_summary = ""
    if summarize and any(r.success for r in results):
        combined_text = "\n\n".join(
            f"[{r.url}]\n{r.content[:2000]}"
            for r in results if r.success
        )
        combined_summary = _summarize_with_claude(combined_text, query, skill_content)

    data = {
        "query": query,
        "total_urls": len(urls),
        "crawled": len(filtered_urls),
        "blocked_urls": blocked,
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

