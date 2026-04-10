# -*- coding: utf-8 -*-
"""
Web Search Tool — CDP 공식 사이트 실시간 검색

외부 검색 API 없이, CDP 공식 사이트를 직접 크롤링하여 최신 정보를 수집합니다.
Tavily/Brave API가 있으면 우선 사용, 없으면 direct crawl fallback.
"""
import re
import logging
import time
from typing import List, Dict, Optional
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)

# CDP 공식 검색 대상 사이트
CDP_SEARCH_URLS = {
    "cdp_main": "https://www.cdp.net/en",
    "cdp_guidance": "https://www.cdp.net/en/guidance/guidance-for-companies",
    "cdp_scores": "https://www.cdp.net/en/scores",
    "cdp_disclosure": "https://www.cdp.net/en/companies-discloser",
    "cdp_responses": "https://www.cdp.net/en/responses",
}

# 실시간 검색이 필요한 키워드
REALTIME_KEYWORDS = [
    "언제", "일정", "발표", "최신", "올해", "2025", "2026",
    "배포", "업데이트", "변경", "마감", "deadline", "schedule",
    "release", "when", "latest", "new", "공지", "안내",
]


def needs_web_search(question: str) -> bool:
    """질문에 실시간 정보가 필요한 키워드가 포함되어 있는지 확인."""
    q_lower = question.lower()
    return any(kw in q_lower for kw in REALTIME_KEYWORDS)


def search_cdp_sites(query: str, max_pages: int = 3) -> List[Dict[str, str]]:
    """
    CDP 공식 사이트를 크롤링하여 관련 정보를 검색합니다.

    Returns: [{"url": str, "title": str, "content": str}, ...]
    """
    from backend.core.crawler import WebCrawler

    results = []
    crawler = WebCrawler()

    # 1. CDP 공식 페이지 직접 크롤링
    urls_to_crawl = list(CDP_SEARCH_URLS.values())[:max_pages]

    for url in urls_to_crawl:
        try:
            result = crawler.fetch(url)
            if result.success and result.content and len(result.content) > 100:
                # 관련성 체크: 쿼리 키워드가 콘텐츠에 포함되는지
                q_words = [w for w in query.lower().split() if len(w) > 1]
                content_lower = result.content.lower()
                relevance = sum(1 for w in q_words if w in content_lower)

                if relevance > 0 or len(results) == 0:
                    results.append({
                        "url": url,
                        "title": result.title or url,
                        "content": result.content[:2000],
                        "relevance": relevance,
                    })
        except Exception as e:
            logger.warning("Search crawl failed for %s: %s", url, e)

    # 2. Google Custom Search fallback (if SEARCH_API_KEY is set)
    try:
        from backend.core.config import settings
        search_key = getattr(settings, "SEARCH_API_KEY", "")
        if search_key:
            google_results = _google_search(query + " site:cdp.net", search_key)
            results.extend(google_results)
    except Exception:
        pass

    # Sort by relevance
    results.sort(key=lambda x: x.get("relevance", 0), reverse=True)
    return results[:3]


def _google_search(query: str, api_key: str) -> List[Dict]:
    """Google Custom Search API (optional)."""
    import urllib.request
    import json
    import ssl

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    try:
        url = f"https://www.googleapis.com/customsearch/v1?q={quote_plus(query)}&key={api_key}&cx=cdp_search&num=3"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
            data = json.loads(resp.read())
        return [
            {"url": item["link"], "title": item["title"], "content": item.get("snippet", ""), "relevance": 5}
            for item in data.get("items", [])[:3]
        ]
    except Exception as e:
        logger.warning("Google search failed: %s", e)
        return []


def format_search_context(results: List[Dict]) -> str:
    """검색 결과를 LLM 컨텍스트 형태로 포맷팅."""
    if not results:
        return ""

    parts = ["[웹 검색 결과]"]
    for i, r in enumerate(results, 1):
        parts.append(f"\n출처 {i}: {r['title']}")
        parts.append(f"URL: {r['url']}")
        parts.append(r["content"][:800])
    return "\n".join(parts)


def format_search_sources(results: List[Dict]) -> List[str]:
    """검색 결과에서 출처 URL 목록 추출."""
    return [f"{r['title']} ({r['url']})" for r in results if r.get("url")]
